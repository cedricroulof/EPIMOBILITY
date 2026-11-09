"""End-to-end test: the platform actually running (server process, real database, full demo dataset of
1,000 students loaded at startup), driven only over HTTP, the way the web and mobile clients will.

    E2E_BASE_URL=http://localhost:8000 pytest tests/e2e   # against a FRESH instance (e.g. docker compose, in CI)
    pytest tests/e2e                                      # no variable: starts uvicorn on a throwaway SQLite database
"""

import os
import socket
import subprocess
import sys
import time

import httpx2
import pytest

PASSWORD = os.environ.get("DEMO_PASSWORD", "demo1234")
BUDGET_MS = 2000  # full 1,000 × 100 run (read, engine, 1,000 assignments written) in one HTTP request


@pytest.fixture(scope="module")
def http(tmp_path_factory):
    base = os.environ.get("E2E_BASE_URL")
    proc = None
    if not base:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        db = tmp_path_factory.mktemp("e2e") / "e2e.db"
        env = {**os.environ, "DATABASE_URL": f"sqlite:///{db}", "DEMO_PASSWORD": PASSWORD}
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
            env=env,
        )
        base = f"http://127.0.0.1:{port}"
    client = httpx2.Client(base_url=base, timeout=30)
    for _ in range(120):  # first startup loads the demo dataset
        try:
            if client.get("/api/health").status_code == 200:
                break
        except httpx2.TransportError:
            pass
        time.sleep(0.5)
    else:
        pytest.fail(f"API unreachable at {base}")
    yield client
    client.close()
    if proc:
        proc.terminate()
        proc.wait(10)


def login(http, email):
    r = http.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_full_assignment_campaign(http):
    # 1. A student browses the catalogue and enters their 5 wishes.
    student = login(http, "etudiant1@exemple.test")
    catalogue = http.get("/api/universities", headers=student).json()
    assert len(catalogue) == 100
    assert {u["continent"] for u in catalogue} >= {"Europe", "Asie", "Afrique", "Océanie"}
    wishes = [u["id"] for u in sorted(catalogue, key=lambda u: u["min_gpa"])[:5]]  # reachable destinations
    assert http.put("/api/me/wishes", json={"wishes": wishes}, headers=student).status_code == 200

    # 2. The same account, from another client (web cookie instead of mobile Bearer), sees the same wishes.
    web = httpx2.Client(base_url=str(http.base_url), timeout=30)
    web.post("/api/auth/login", json={"email": "etudiant1@exemple.test", "password": PASSWORD})
    assert web.get("/api/me/wishes").json()["wishes"] == wishes
    web.close()

    # 3. The administration runs both algorithms on the full cohort and compares them.
    admin = login(http, "admin@exemple.test")
    assert http.get("/api/admin/runs", headers=student).status_code == 403
    config_id = http.get("/api/admin/configs", headers=admin).json()[0]["id"]
    t0 = time.perf_counter()
    gs = http.post("/api/admin/runs", json={"config_id": config_id, "algorithm": "gale_shapley"}, headers=admin)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert gs.status_code == 201, gs.text
    gs = gs.json()
    print(
        f"\nGale-Shapley run 1000 × 100: {elapsed_ms:.0f} ms end-to-end HTTP, including engine {gs['duration_ms']} ms"
    )
    assert elapsed_ms < BUDGET_MS
    assert gs["metrics"]["students"] == 1000 and gs["metrics"]["blocking_pairs"] == 0
    boston = http.post("/api/admin/runs", json={"config_id": config_id, "algorithm": "boston"}, headers=admin).json()
    assert boston["metrics"]["blocking_pairs"] > 0  # the comparison shows Boston's instability
    compare = http.get(f"/api/admin/runs/{gs['id']}/compare/{boston['id']}", headers=admin).json()
    assert compare["moved"], "two different algorithms should move students"

    # 4. Publication, then the student reads their explained result; their wishes are now frozen.
    assert http.post(f"/api/admin/runs/{gs['id']}/publish", headers=admin).status_code == 200
    result = http.get("/api/me/result", headers=student).json()
    assert result["run_id"] == gs["id"] and len(result["explanation"]) == 5
    assert http.put("/api/me/wishes", json={"wishes": wishes}, headers=student).status_code == 409

    # 5. Identical replay, then logout: the token is revoked.
    assert http.post(f"/api/admin/runs/{gs['id']}/replay", headers=admin).json()["identical"] is True
    assert http.post("/api/auth/logout", headers=student).status_code == 204
    assert http.get("/api/me", headers=student).status_code == 401
