"""Tests fonctionnels : chaque règle métier ou de sécurité exposée par l'API, vérifiée par un appel HTTP réel
(en processus) contre une base neuve. Le moteur, déjà couvert en unitaire, est ici traité comme une boîte noire."""

from sqlalchemy.orm import Session as OrmSession

from app import db, services
from engine import generator, rules

PASSWORD = "demo1234"  # mot de passe des comptes du jeu de test (conftest)

DEFAULT_ID = rules.config_id(rules.DEFAULT_CONFIG)


def run(client, admin, algorithm="gale_shapley", seed=7):
    r = client.post(
        "/api/admin/runs", json={"config_id": DEFAULT_ID, "algorithm": algorithm, "seed": seed}, headers=admin
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── authentification et contrôle d'accès (OWASP A01, A07) ─────────────────────
def test_health_and_security_headers(client):
    r = client.get("/api/health")
    assert r.json()["status"] == "ok"
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"


def test_login_failure_is_uniform_then_rate_limited(client):
    unknown = client.post("/api/auth/login", json={"email": "nobody@exemple.test", "password": "x"})
    wrong = client.post("/api/auth/login", json={"email": "admin@exemple.test", "password": "x"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()  # ne révèle pas si le compte existe
    codes = [
        client.post("/api/auth/login", json={"email": "admin@exemple.test", "password": "x"}).status_code
        for _ in range(5)
    ]
    assert codes[-1] == 429
    ok = client.post("/api/auth/login", json={"email": "admin@exemple.test", "password": PASSWORD})
    assert ok.status_code == 429  # même le bon mot de passe est bloqué pendant la fenêtre


def test_web_cookie_session_and_logout(client):
    r = client.post("/api/auth/login", json={"email": "etudiant1@exemple.test", "password": PASSWORD})
    assert "httponly" in r.headers["set-cookie"].lower() and "samesite=lax" in r.headers["set-cookie"].lower()
    assert client.get("/api/me").json()["role"] == "student"  # le cookie suffit (client web)
    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.set("session", r.json()["token"])  # jeton volé après déconnexion : révoqué côté serveur
    assert client.get("/api/me").status_code == 401


def test_every_route_but_health_and_login_requires_a_session(client):
    for path in ("/api/me", "/api/universities", "/api/me/wishes", "/api/me/result", "/api/admin/runs"):
        assert client.get(path).status_code == 401, path


def test_roles_are_enforced_server_side(client, admin, student):
    assert client.get("/api/admin/runs", headers=student).status_code == 403
    assert client.post("/api/admin/runs", json={}, headers=student).status_code == 403
    assert client.get("/api/me/wishes", headers=admin).status_code == 403


# ── vœux : validation et isolement entre étudiants ───────────────────────────
def test_wishes_validation(client, student):
    ids = [u["id"] for u in client.get("/api/universities", headers=student).json()]
    for bad in (ids[:4], ids[:4] + ids[:1], ids[:4] + ["NOPE"]):
        assert client.put("/api/me/wishes", json={"wishes": bad}, headers=student).status_code == 422, bad
    wanted = ids[5:10][::-1]
    assert client.put("/api/me/wishes", json={"wishes": wanted}, headers=student).status_code == 200
    assert client.get("/api/me/wishes", headers=student).json()["wishes"] == wanted  # ordre conservé


def test_a_student_only_touches_their_own_wishes(client, student, login):
    other = login("etudiant2@exemple.test")
    before = client.get("/api/me/wishes", headers=other).json()
    ids = [u["id"] for u in client.get("/api/universities", headers=student).json()]
    client.put("/api/me/wishes", json={"wishes": ids[:5]}, headers=student)
    assert client.get("/api/me/wishes", headers=other).json() == before


# ── configurations versionnées ───────────────────────────────────────────────
def test_config_validation_reports_every_error(client, admin):
    bad = {"criteria": [{"key": "gpaa", "weight": "x", "min": 1, "max": 0}], "eliminatory": [{"key": "gpa", "op": "~"}]}
    r = client.post("/api/admin/configs", json=bad, headers=admin)
    assert r.status_code == 422
    for fragment in ("'gpaa' inconnue", "weight", "min", "op inconnu", "exactement un"):
        assert fragment in r.json()["detail"], fragment


def test_config_versions_are_content_addressed(client, admin):
    cfg = {**rules.DEFAULT_CONFIG, "criteria": [{"key": "gpa", "weight": 1, "min": 0, "max": 4}]}
    first = client.post("/api/admin/configs", json=cfg, headers=admin)
    renamed = client.post("/api/admin/configs", json={**cfg, "name": "Autre nom"}, headers=admin)
    assert (first.status_code, renamed.status_code) == (201, 200)  # renommer ne crée pas de version
    assert first.json()["id"] == renamed.json()["id"] != DEFAULT_ID


# ── runs : affectation, publication, résultat expliqué ───────────────────────
def test_result_is_hidden_until_publication(client, admin, student):
    run(client, admin)
    assert client.get("/api/me/result", headers=student).status_code == 404


def test_run_publish_and_explained_result(client, admin, student):
    gs, boston = run(client, admin), run(client, admin, "boston")
    assert gs["metrics"]["blocking_pairs"] == 0 and gs["metrics"]["violations"] == []
    assert client.post(f"/api/admin/runs/{boston['id']}/publish", headers=admin).status_code == 409
    assert client.post(f"/api/admin/runs/{gs['id']}/publish", headers=admin).status_code == 200

    res = client.get("/api/me/result", headers=student).json()
    wishes = client.get("/api/me/wishes", headers=student).json()["wishes"]
    assert [e["university"] for e in res["explanation"]] == wishes
    statuses = {e["status"] for e in res["explanation"]}
    assert statuses <= {"assigned", "rejected", "ineligible", "not_considered"}
    if res["university_id"]:
        assert res["explanation"][res["rank"] - 1]["status"] == "assigned"
    put = client.put("/api/me/wishes", json={"wishes": wishes}, headers=student)
    assert put.status_code == 409  # vœux fermés après publication


def test_replay_is_identical_even_after_data_changed(client, admin, student):
    original = run(client, admin)
    ids = [u["id"] for u in client.get("/api/universities", headers=student).json()]
    client.put("/api/me/wishes", json={"wishes": ids[-5:]}, headers=student)  # la base bouge…
    r = client.post(f"/api/admin/runs/{original['id']}/replay", headers=admin).json()
    assert r["identical"] is True and r["run"]["replay_of"] == original["id"]  # …le rejeu lit le snapshot
    assert r["run"]["input_hash"] == original["input_hash"]


def test_compare_lists_moved_students(client, admin):
    gs, boston = run(client, admin), run(client, admin, "boston")
    r = client.get(f"/api/admin/runs/{gs['id']}/compare/{boston['id']}", headers=admin).json()
    assert r["a"]["algorithm"] == "gale_shapley" and r["b"]["algorithm"] == "boston"
    assert all(m["a"] != m["b"] for m in r["moved"])


def test_run_input_errors(client, admin):
    bad_cfg = client.post("/api/admin/runs", json={"config_id": "nope", "algorithm": "gale_shapley"}, headers=admin)
    bad_algo = client.post("/api/admin/runs", json={"config_id": DEFAULT_ID, "algorithm": "magic"}, headers=admin)
    assert (bad_cfg.status_code, bad_algo.status_code) == (404, 422)


# ── contrat base → moteur (le vrai contrat du rejeu, §4) ─────────────────────
def test_db_to_engine_mapping_is_lossless():
    """Ce que le moteur lit depuis la base est exactement ce que le générateur a produit, au bit près."""
    from sqlalchemy import create_engine

    engine = create_engine("sqlite://")
    db.Base.metadata.create_all(engine)
    with OrmSession(engine) as s:
        services.seed(s, n_students=60, n_unis=12, password=PASSWORD)
        assert generator.dataset_hash(*services.load_inputs(s)) == generator.dataset_hash(
            *generator.generate("nominal", 60, 12, 42)
        )
