# Backend testing strategy

One command runs everything: `pnpm test` (or `uv run pytest`), 39 tests, ≈ 15 s, with no Docker or database to install.

The tests follow a pyramid: many fast, precise tests at the bottom, a single slow, broad scenario at the top.
Each level covers what the level below **cannot see**, without repeating what it already proves.

| Level | File | Count | Duration | What it proves |
|---|---|---:|---:|---|
| Unit | `packages/engine/tests`, `packages/generator/tests` | 23 | < 1 s | Rules engine, Gale-Shapley and Boston, stability check, generator reproducibility, golden hashes |
| Functional | `apps/api/tests/functional` | 15 | ≈ 3 s | Every business and security rule exposed by the API |
| End-to-end | `apps/api/tests/e2e` | 1 scenario | ≈ 5 s (≈ 1 min in CI with the Docker build) | The running platform, driven over HTTP the way the web and mobile clients will do it |
| Performance | `packages/engine/benchmark/run.py` | 68 checks | ≈ 6 s | Computation time per algorithm, from 1,000 to 50,000 students, and quantified comparison |
| Conventions | `.pre-commit-config.yaml` | – | – | Commit messages, lint, format, no private keys |

## Unit: the engine, in isolation

**Why this level.** The project brief requires at least tests on the rules engine, the algorithms (including the
automatic stability check) and the generator's reproducibility. `packages/engine` is a pure module (no I/O),
so it can be tested without a database or server, in milliseconds: a regression is pinpointed to the exact function.

**What is covered.** Configuration validation (all errors at once, typos rejected),
eliminatory thresholds, bonuses, adding a criterion without code, total tie-break, per-university weights;
Gale-Shapley stable on the six scenarios, Boston unstable and detected as such, blocking pairs on a hand-built
instance; replay insensitive to input order; fairness of the English scale; reproducible
generator.

**Why golden hashes.** `test_golden_hashes_pin_engine_behaviour` breaks as soon as the engine changes
behavior, even subtly. This is intended: `ENGINE_VERSION` is then incremented, otherwise an old replay could no
longer be explained.

## Functional: the API, one rule per test

**Why this level.** The engine sees neither HTTP, nor sessions, nor permissions, nor a database. Yet most of the
project brief's security requirements (separate accounts, permissions checked server-side, OWASP) live there.

**How.** FastAPI's `TestClient` (real HTTP requests, in process) against an in-memory SQLite database, **fresh
for each test**: no test depends on another, and execution order does not matter. No mocks: the engine
is pure and the database is a real SQL database, so the real behavior is what gets tested.

**What is covered.**
- Security: routes closed without a session; roles checked server-side, a student cannot reach `/admin` (OWASP A01);
  identical failure message whether or not the account exists, then lockout after 5 failures (A07); `HttpOnly`
  `SameSite=Lax` cookie; token revoked at logout; security headers.
- Wishes: exactly 5, distinct, existing; order preserved; a student can only touch their own; closed after
  publication.
- Rules: invalid configuration rejected with all its errors; versions identified by their content (renaming
  does not create a version).
- Runs: result invisible before publication; Boston not publishable; per-wish explanation consistent with
  the assignment; identical replay even after the database is modified; what-if comparison.
- Database → engine contract: what the engine reads from the database is, bit for bit, what the generator produced.
  This is the real replay contract (architecture §4).

## End-to-end: what will be deployed

**Why this level.** It is the only one that exercises what the lower levels replace: the production Docker
image, PostgreSQL (not SQLite), loading the full demo dataset at startup (1,000 students,
100 universities), the uvicorn server, both session transports (Bearer for mobile, cookie for web).
It also checks the **newcomer test**: if `docker compose up` does not give a usable platform, CI
fails.

**Why a single scenario.** An end-to-end test is slow and breaks for many reasons. So it covers the
one critical path, a complete assignment campaign: a student enters their wishes, the same account finds them
from another client, the admin launches both algorithms and compares them, publishes, the student reads their
explained result, their wishes are frozen, the run replays identically, logout revokes the token. The details of
each rule stay at the functional level.

**End-to-end performance measurement.** The project brief asks for measured performance; the benchmark measures
only the engine. The e2e test times `POST /admin/runs` on the full cohort (database read, engine, writing the 1,000
explained assignments) and prints the result in the CI log. Measured locally: ≈ 190 ms on PostgreSQL
(Docker), ≈ 315 ms on SQLite. The assertion is at 2 s (`BUDGET_MS`), four times the 500 ms budget of ADR-0004,
so that it does not fail at random on a shared runner: it catches an order-of-magnitude regression, and the exact
figure can be read in the log.

**Two modes.** Without the variable, the test starts uvicorn itself on a throwaway SQLite database: it runs anywhere
with `uv run pytest`. In CI, `E2E_BASE_URL` points it at the platform started by `docker compose up --build`. It
requires a **fresh** instance: the scenario publishes results, which closes the wishes.

## Performance: the benchmark

`packages/engine/benchmark/run.py` is an assertion suite (68 checks: invariants, stability, replay, detection of
Boston's instability, criterion without code) and a timing run per algorithm and per cohort size. It runs in
CI on every PR; the report is published as a pipeline artifact, not committed: timings vary from one machine to
another, only the checks are comparable. Protocol: [`benchmark-protocol.md`](benchmark-protocol.md).

## Conventions

The pre-commit hooks (format, lint, private keys, commit message) run locally on every commit, and CI runs them
again on the whole repository: a hook bypassed locally (`--no-verify`) is caught in the PR. Details in
[`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Running only a part

```bash
uv run pytest packages                                          # unit (engine, generator)
uv run pytest apps/api/tests/functional                         # functional
uv run pytest -k replay                                         # tests whose name contains "replay"
uv run pytest packages/engine/tests/test_engine.py::test_config_id_tracks_content
uv run pytest apps/api/tests/e2e -s                             # prints the measured run time
E2E_BASE_URL=http://localhost:8000 uv run pytest apps/api/tests/e2e  # against a fresh Docker platform
pnpm bench                                                      # benchmark, rewrites docs/technical/benchmark-results.md
```

## Not covered yet, and when to add it

| Gap | When |
|---|---|
| OpenAPI contract test (frozen schema, compared in CI) | as soon as the web and mobile apps generate their client from `/openapi.json` |
| JSON schema validation of the file of 100 real universities | with the data file |
| Coverage measurement (`pytest-cov`) | if the team wants a threshold in CI |
| Concurrent load (mass wish entry when wishes open) | if the demo calls for it |
| Mobile app tests (logic and UI) | in the mobile part, required by the project brief |
