# Backend architecture — International mobility platform

> Scope: everything behind the API. The website and the mobile app are two clients of this API.
> The matching engine is **implemented, tested and measured** (`packages/engine`, `packages/generator`, `benchmark-results.md`);
> the API exists as a proof of concept (`apps/api`, see `testing.md`); the database and the deployment are specified so they can be built as is.
> This document was reviewed by an outside developer; their remarks are incorporated, and the questions that remain
> open are listed in §14. Chosen stack: Python, FastAPI, PostgreSQL (ADR-0001, accepted).

## 1. What the project brief requires of the backend, and the chosen response

| Brief requirement | Response | Section |
|---|---|---|
| Rules the administration can change without a developer; new criterion without touching the code | Interpreted JSON configuration (weights, eliminatory thresholds, bonuses/penalties, tie-break, per-university weights); free-form attributes on the student and on the university | §5, ADR-0002 |
| Versioned configurations, identical replay of an assignment | Immutable configurations identified by the hash of their content; each run keeps the exact snapshot of its inputs, its seed and the engine version | §6, ADR-0003 |
| ≥ 2 algorithms including Gale-Shapley; quantified comparison; verified stability | Gale-Shapley (deferred acceptance) + Boston (immediate acceptance); metrics and blocking pair detector independent of the algorithms | §5.3, ADR-0006 |
| Explained result: "why this wish and not the previous one" | Structured per-wish explanation, computed during the run, verified, stored with the assignment | §5.4 |
| What-if mode: two configurations side by side | Two runs, compared server-side (metrics + students moved) | §7 |
| Same backend for web and mobile; synchronized wishes | A single JSON REST API; wishes exist only server-side | §7, §8 |
| Catalog viewable offline; notification at publication | `ETag` on the catalog; FCM topic push (a single call) | §8 |
| Separate student/admin accounts, server-side permissions, OWASP Top 10 | Opaque sessions, role check through a dependency, student routes without identifiers, SPA served by the API | §9, ADR-0005 |
| Computation time measured for 1,000 students, per algorithm | Reproducible benchmark; 500 ms budget per run, measured ≈ 16 ms excluding the database | §10, ADR-0004 |
| Engine / algorithm / generator tests in one command; CI/CD; one-command installation | `pytest`; GitHub Actions; Docker Compose with demo dataset loaded at startup | §11 |
| Real, sourced data, credited photos | JSON schema of `data/universities.json` checked by a test | §11 |

## 2. Overview

```
        Browser (SPA served by the API)          Mobile (native)
                    │        HTTPS / JSON              │
                    └───────────────┬──────────────────┘
                                    ▼
      ┌──────────────────────────────────────────┐        ┌───────────────┐
      │ API — FastAPI (single deployable)        │  SQL   │ PostgreSQL 16 │
      │  routers  → validation, auth, roles      │◀──────▶│               │
      │  services → snapshot, run, publication   │        └───────────────┘
      │  engine   → pure module, no I/O          │──1 call──▶ FCM (topic "results")
      └──────────────────────────────────────────┘
```

Three layers, dependencies in one direction only: `routers → services → engine`.

- **engine** (`packages/engine`) knows nothing about HTTP or the database: it takes (universities, students, configuration) and returns (assignment, cutoffs, metrics, explanations). It can be tested and benchmarked without starting anything: that is what was measured.
- **services/** orchestrates: load the configuration, freeze the snapshot (including the lottery), call the engine, persist, publish, notify.
- **routers/** exposes the API: Pydantic schemas (validation at the boundaries), authentication, role-based authorization.

No task queue, no external cache, no second service: a 1,000 × 100 run takes ≈ 16 ms excluding the database (§10) and executes inside the HTTP request. The publication notification goes out as a FastAPI background task (one FCM call).

## 3. Chosen stack

| Need | Choice | Why (details in ADR-0001) |
|---|---|---|
| Language / framework | Python 3.12 (CI and production; the engine runs on 3.10 through 3.14), FastAPI, Pydantic v2 | Automatically generated OpenAPI, declarative validation, little code |
| Database | PostgreSQL 16, SQLAlchemy 2, Alembic | JSONB for configurations, snapshots, free-form attributes; integrity constraints in the database; versioned migrations |
| Passwords / sessions | argon2-cffi, opaque sessions in the database | ADR-0005 |
| Tests / quality | pytest, ruff (lint + format), pre-commit | One command for everything |
| Containers / CI / CD | Docker Compose, GitHub Actions, Fly.io (API, machine that does not go to sleep) + Neon (Postgres), free tiers | Deployment on every merge to `main`; Render's free tier ruled out: sleep mode ≈ 50 s, fatal in a demo |
| Mobile push | FCM HTTP v1, sending by topic | One call for the whole cohort, iOS and Android |

The engine uses only the standard library: it can be tested and measured without a database or server.

## 4. Data model

```
users          id uuid PK · email unique · password_hash · role ∈ {student, admin} · created_at
sessions       token_hash text PK · user_id→users · created_at · expires_at · user_agent        ← ADR-0005
students       user_id PK→users · gpa numeric(3,2) · english_test ∈ {TOEIC, IELTS} · english_score numeric
               · associative int · attributes jsonb '{}'            ← criteria added without code (personal project, absences, lottery…)
universities   id text PK (slug) · name · city · country · continent · lat · lng
               · description · fields text[] · teaching_language · local_life
               · cost_of_living jsonb {housing, food, transport, monthly_total, source}
               · photos jsonb [{url, author, license, alt}]           ← mandatory credits (golden rule of the project brief)
               · capacity int · min_gpa numeric · min_cefr text       ← admission requirements (fictional but consistent)
               · attributes jsonb '{}'                                ← thresholds added without code (e.g. min_associative)
               · stay jsonb {duration_months, period, fees} · sources jsonb [{label, url}] · updated_at
wishes         student_id→students · rank smallint 1..5 · university_id→universities · updated_at
               PK(student_id, rank) · UNIQUE(student_id, university_id)    ← 5 ordered, distinct wishes, enforced by the database
rule_configs   id text PK = content hash (excluding `name`) · name · config jsonb · parent_id→rule_configs
               · created_by→users · created_at                            ← IMMUTABLE: modifying = creating a new row
runs           id uuid PK · config_id→rule_configs · algorithm · seed int · engine_version text · status ∈ {done, failed} · error text
               · input_snapshot jsonb · input_hash · output_hash · metrics jsonb · duration_ms
               · created_by · created_at · published_at nullable · replay_of→runs nullable
assignments    run_id→runs · student_id→students · university_id→universities nullable · rank smallint nullable
               · score numeric · explanation jsonb · PK(run_id, student_id)
devices        id · user_id→users · platform ∈ {ios, android} · token text unique · created_at
settings       key text PK · value jsonb                                   ← wishes_open (only key for now)
```

Field dictionary: generated from the SQLAlchemy models into `docs/data-model.md`; the names above are those of the engine (`packages/generator`), to avoid any translation between layers. **The database → engine mapping (`services/runs.py : snapshot()`) is the real replay contract: it is covered by a test that loads the demo dataset, builds the snapshot, and checks the expected hash.**

Integrity rules enforced by the database rather than by the code: at most 5 distinct wishes (primary key + unique constraint), immutable configurations (no `UPDATE`/`DELETE` granted to the application role on `rule_configs`), one assignment per student and per run (composite primary key), students cannot be deleted while a run references them (`ON DELETE RESTRICT`).

## 5. Rules and matching engine (`packages/engine`)

### 5.1 Configuration format (valid, annotated example)

```jsonc
{
  "name": "Fall 2027 intake — standard weights",      // not part of the hash: renaming does not create a version
  "criteria": [                                        // score = Σ weight × pct, pct = (value − min) / (max − min) × 100 clamped to [0, 100]
    { "key": "gpa",         "weight": 0.5,  "min": 0, "max": 4 },
    { "key": "english_pct", "weight": 0.3,  "min": 0, "max": 100 },  // common TOEIC/IELTS scale by CEFR bands (ADR-0007)
    { "key": "associative", "weight": 0.2,  "min": 0, "max": 100 },
    { "key": "absences",    "weight": -0.1, "min": 0, "max": 20, "default": 0 }  // negative weight = penalty; default: missing attribute = 0
  ],
  "eliminatory": [                                     // all must be true, otherwise ineligible for this university
    { "key": "gpa",          "op": ">=", "ref": "min_gpa" },          // ref = university attribute (built-in or `attributes`)
    { "key": "english_cefr", "op": ">=", "ref": "min_cefr" },         // levels compared by ordinal A1 < … < C2
    { "key": "english_cefr", "op": ">=", "value": "B1" },             // constant: a level spelled out as text is accepted
    { "key": "absences",     "op": "<",  "value": 15, "default": 0 }  // WITHOUT default, a student without the attribute would be ineligible everywhere
  ],
  "bonuses": [                                         // points added if the condition is true (negative = penalty)
    { "key": "personal_project", "op": "==", "value": true, "points": 10 }
  ],
  "overrides": {                                       // university-specific weights (criteria and/or bonuses)
    "U017": { "criteria": [ { "key": "english_pct", "weight": 0.7, "min": 0, "max": 100 },
                            { "key": "gpa",         "weight": 0.3, "min": 0, "max": 4 } ] }
  },
  "tie_break": [                                       // tie-break on equal scores; the student id is always added last
    { "key": "gpa", "order": "desc" },
    { "key": "english_pct", "order": "desc" },
    { "key": "lottery", "order": "asc" }               // seeded lottery number, drawn at snapshot time, shown in the explanation
  ]
}
```

Operators: `>= <= > < == != in`. No free-form expressions, no `eval`. `rules.validate(config, student_keys, university_keys)` returns **all** errors at once: types, operators, unknown CEFR levels, and **keys that do not exist in any data** (a typo such as `gpaa` is rejected). The API calls `validate` with the keys actually present in the database; `GET /admin/configs/keys` exposes this list so that the admin form offers the right keys.

Resolving a student key: derived (`english_cefr`, `english_pct`), built-in (`gpa`, `english_score`, `associative`), then `attributes`. On the university side: `capacity`, `min_gpa`, `min_cefr`, then `attributes`. Missing student attribute: `default` if it exists, otherwise 0 points (criterion) or ineligible (threshold, the cautious choice). University attribute missing in a `ref`: the threshold does not apply to that university.

### 5.2 Adding a criterion without modifying the code

1. Fill in the attribute: `PUT /admin/students/attributes` (CSV `student_id,key,value` or JSON) in one request for the whole cohort, or `PATCH /admin/students/{id}` one at a time; likewise `PUT /admin/universities/{id}` for a university-side threshold.
2. In the admin area, add the entry to `criteria`, `bonuses`, `eliminatory` or `tie_break`; validate; save → new version.
3. Launch a run with this version.

Proof: `test_new_criterion_without_code_changes_outcome`, `test_university_attribute_threshold_without_code`, and the "New criterion without code" check of the benchmark.

### 5.3 Algorithms

Shared preprocessing (`algorithms.Problem`): validation of the configuration against the data and of the inputs (distinct wishes, known universities, capacities ≥ 0), score of each (student, wish), eligibility, and for each university the preference order of its eligible candidates: descending score, then `tie_break`, then id. A **total and strict** order: the condition for the uniqueness of the result and for replay.

| | Gale-Shapley (students proposing, capacities) | Boston (immediate acceptance) |
|---|---|---|
| Principle | Each student proposes to their best remaining wish; the university tentatively keeps its best candidates up to its seats and evicts the worst one, who proposes again | Round 1: everyone applies to their 1st wish, final admissions; round 2: rejected students apply to their 2nd wish on the remaining seats; etc. |
| Complexity | O(Σ wishes × log capacity), at most 5,000 proposals | O(Σ wishes × log) |
| Properties | Stable (0 blocking pairs, guaranteed), optimal for students among stable assignments, not manipulable by them | Maximizes the number of 1st wishes served, but unstable and manipulable (incentive to "lie" about one's 1st wish) |
| Role | Publication algorithm | Point of comparison in what-if mode; its publication is rejected (`409`) |

Without `overrides`, all universities rank candidates in the same order (only eligibility differs) and Gale-Shapley coincides with serving students in descending score order. With `overrides`, the rankings differ from one university to another and stability becomes a real property: the benchmark shows it ("nominal + overrides").

**Automatic stability check** (`algorithms/stability.py`, `blocking_pairs`): independent of the algorithms, it reads only the final assignment. A (student, university) pair is blocking if the student prefers that university to their assignment and the university has a free seat or prefers the student to its worst admitted student. ≈ 0.3 ms for 1,000 × 100; result stored in `runs.metrics`. The benchmark also requires it to *detect* instability (Boston: 116 pairs on the nominal scenario).

### 5.4 Per-student explanation

For each wish, a status and what justifies it, stored in `assignments.explanation`:

```json
[
  {"rank": 1, "university": "U017", "status": "ineligible", "score": 71.2, "failed": [{"key": "english_cefr", "value": "B2", "op": ">=", "threshold": "C1", "ref": "min_cefr"}]},
  {"rank": 2, "university": "U042", "status": "rejected",   "score": 71.2, "cutoff": 74.9},
  {"rank": 3, "university": "U008", "status": "assigned",   "score": 70.4, "cutoff": 66.0},
  {"rank": 4, "university": "U051", "status": "not_considered", "score": 71.2},
  {"rank": 5, "university": "U090", "status": "not_considered", "score": 71.2}
]
```

- `score` is the student's score **for this university** (it varies if the university has an `override`).
- `cutoff`: score of the last admitted student at this university (Gale-Shapley: final cutoff; Boston: cutoff of the round in which the student applied). `cutoff: null` on a `rejected` entry means "no seat was open" (capacity 0, or already full before this round in Boston): the client displays this label.
- Consistency checked on the 1,000 students by `algorithms/metrics.py`, `explanation_violations`: a rejected student never exceeds the stated cutoff, an admitted student always reaches it, and in Gale-Shapley a rejection without a cutoff only exists for zero capacity.

The text ("Rejected: the last admitted student had 74.9, your score is 71.2") is written by the client from this structure: translation and accessible rendering remain its responsibility.

### 5.5 Determinism and replay

- Score rounded to 4 decimal places; total preference order (id last); no reliance on row order (verified: shuffled inputs ⇒ same `output_hash`).
- Tie-break on exact ties: **lottery** number `lottery` drawn by `generator.draw_lottery(students, run.seed)` at snapshot time, in id order, stored in `attributes` (and therefore in the snapshot), configurable in `tie_break`, visible in the explanation. Without it, the id would break the tie: legal but arbitrary and invisible.
- `runs.engine_version` = `engine.ENGINE_VERSION`. A replay that returns `identical: false` with a different version is explained as such. The golden hashes (`test_golden_hashes_pin_engine_behaviour`) break as soon as the engine changes behavior: this is intended, the version is then incremented.

## 6. Run lifecycle

```
Admin ─POST /admin/runs {config_id, algorithm, seed?}─▶ API
  1. load rule_configs[config_id]  (immutable)
  2. snapshot: students (fields, attributes, wishes) + universities (capacity, thresholds, attributes); `lottery` draw with seed
     → runs.input_snapshot, input_hash, seed, engine_version
  3. engine: Problem (validates config ⊗ data) → algorithm → metrics + blocking pairs + explanations   ≈ 16 ms
  4. persist run + 1,000 assignments (one multi-row INSERT), one transaction
  5. 201 {run}  ← immediate comparison
Admin ─POST /admin/runs/{id}/publish─▶ published_at = now · wishes_open = false · background task: 1 FCM call on the "results" topic
Student ─GET /me/result─▶ assignment + explanation of the latest published run (published_at max)
```

- **Replay**: `POST /admin/runs/{id}/replay` reads back `input_snapshot`, `config_id`, `seed`, reruns the engine, creates a run `replay_of = id`, responds with `{"identical": bool, "engine_version": {"original", "current"}}`. Independent of the current database state.
- **What-if**: `GET /admin/runs/{a}/compare/{b}`: two metric blocks + students whose assignment differs. The benchmark shows that a weight change moves ≈ 100 students out of 1,000.
- **Failure**: engine exception ⇒ transaction rolled back, `status = failed`, `error` = the `validate` or invalid inputs message, nothing is published.
- **Multiple publications**: the most recent one is authoritative and replaces the previous one; the history remains viewable on the admin side.

Size of a 1,000 × 100 snapshot: ≈ 180 KB of JSON (measured). One hundred runs ≈ 18 MB.

## 7. REST API

Conventions: JSON, `snake_case`, `application/problem+json` errors (RFC 9457) with `errors[]` tied to fields, ISO 8601 UTC dates, OpenAPI on `/docs` and `/openapi.json`. Pagination `?limit=&offset=` on admin lists only.

| Method and path | Role | Behavior |
|---|---|---|
| `POST /auth/login` · `POST /auth/logout` · `GET /me` | all | session cookie (web) or Bearer token (mobile), same mechanism |
| `GET /universities` (filters `continent, country, language, max_cefr, max_cost, q`) · `GET /universities/{id}` | student, admin | `ETag` + `Cache-Control: max-age=300`; `304` if unchanged |
| `GET /me/wishes` · `PUT /me/wishes` `[id×5]` | student | exactly 5 distinct, existing ids, otherwise `400`; atomic replacement; `409` if `wishes_open = false`; returns `updated_at` |
| `GET /me/result` | student | latest published run; `404` until something is published |
| `POST /me/devices {platform, token}` · `DELETE /me/devices/{token}` | student | registration + subscription to the FCM topic `results` |
| `GET /admin/configs` · `GET /admin/configs/{id}` · `GET /admin/configs/keys` · `POST /admin/configs/validate` · `POST /admin/configs` | admin | idempotent `POST`: same content ⇒ `200` with the existing version, otherwise `201` (`parent_id` = starting version); `keys` = usable keys |
| `POST /admin/runs` · `GET /admin/runs` · `GET /admin/runs/{id}` · `GET /admin/runs/{id}/assignments?format=json\|csv` | admin | synchronous run, `201`; optional `seed` (default: random, stored) |
| `GET /admin/runs/{a}/compare/{b}` · `POST /admin/runs/{id}/replay` · `POST /admin/runs/{id}/publish` | admin | §6; `publish` rejects a Boston or `failed` run (`409`) |
| `GET /admin/stats` | admin | `{demand: [{university_id, wishes_by_rank: [n1..n5], capacity}], gpa_hist, english_hist, associative_hist, wishes_by_continent, published_run_metrics}` |
| `GET /admin/students` · `PATCH /admin/students/{id}` · `PUT /admin/students/attributes` | admin | free-form attributes; bulk CSV/JSON import |
| `POST /admin/students/generate {seed, scenario, n}` | admin | regenerates the fictional cohort; `409` as soon as a run exists (runs reference students) |
| `GET /admin/universities` · `PUT /admin/universities/{id}` | admin | seats, thresholds, attributes, practical info |
| `GET /admin/settings` · `PUT /admin/settings` | admin | `wishes_open` |
| `GET /health` | public | database reachable, API and engine version |

Design rule: **no student route takes a student identifier**. Everything goes through `/me`, resolved from the session. There is no path to another student's data.

## 8. Contract with the mobile app

- **Offline**: `GET /universities` loaded at first launch, stored locally (JSON + images by URL); each time the app opens, conditional `If-None-Match` request, `304` = nothing to download. University pages, map and filters work from this cache.
- **Wish synchronization**: wishes on the server side only; `PUT /me/wishes` replaces the list and returns `updated_at`. Last write wins (one student, two devices: conflict unlikely); add `If-Match` if conflicts appear.
- **Notification**: when a device is registered, the API subscribes it to the FCM topic `results`; at publication, a single data message `{"type": "results_published", "run_id": …}` on the topic. The app displays the notification and refreshes `GET /me/result`. Fallback: polling `GET /me/result` when the app opens. **On the iOS simulator, no real push arrives**: if the target is iOS, the demo uses a real device or the fallback (open question §14).
- **Authentication**: `POST /auth/login` also returns the token in the body; the app stores it in the keychain and sends it as `Authorization: Bearer`.

## 9. Security (OWASP Top 10 2021)

| Risk | Measure |
|---|---|
| A01 Access control | `require_role("admin")` on all of `/admin/*`; student routes under `/me` only; API tests that attempt cross-access |
| A02 Cryptography | argon2id; TLS terminated by the host; random 32-byte session tokens, stored hashed (`sessions.token_hash`) |
| A03 Injection | ORM with bound parameters; Pydantic on all inputs; rules = validated data, allowlisted operators, keys checked against the data, no expression evaluation |
| A04 Design | Immutable configurations, snapshots, wishes locked at publication, regeneration forbidden after a run |
| A05 Configuration | Headers (`HSTS`, `X-Content-Type-Options`, `Content-Security-Policy`), SPA served by the API and therefore **no CORS in production** (ADR-0005), debug disabled outside development, `.env.example` |
| A06 Components | `uv.lock`; Dependabot; `pip-audit` in CI |
| A07 Authentication | Rate limiting on `/auth/login` (5 attempts / minute / IP and account); sliding 7-day expiry; rotation at login; identical message whether or not the email exists |
| A08 Integrity | Required CI checks; locked dependencies; image built in CI |
| A09 Logging | Structured JSON logs; admin actions (config created, run, publication, import) logged with their author |
| A10 SSRF | No outbound call built from user input (FCM only, fixed URL) |

Fictional data treated as real: no export without the admin role, demo emails at `@exemple.test`.

## 10. Performance

Budget: preparation + assignment + stability check in under 500 ms for 1,000 × 100, so as to fit in the HTTP request (ADR-0004). Measured excluding the database, Apple M3, Python 3.14, median of 5 executions (a single one beyond 1,000 students), `docs/benchmark-results.md`:

| Instance | Gale-Shapley | Boston | of which blocking pair detection |
|---|---:|---:|---:|
| 1,000 × 100 (the required size) | ≈ 16 ms | ≈ 16 ms | 0.3 ms |
| 10,000 × 1,000 | ≈ 0.2 s | ≈ 0.2 s | 3 ms |
| 50,000 × 1,000 | ≈ 1.1 s | ≈ 1.1 s | 40 ms |

The time is dominated by preparation (scores, eligibility, candidate sorting), linear in Σ wishes. Ten times the required size fits in the budget; fifty times exceeds it: this is the threshold at which a task queue would be justified.

**What is not measured yet**: the end-to-end run (`POST /admin/runs`) with reading the 1,000 students, writing the snapshot (≈ 180 KB) and the 1,000 assignments with explanations (≈ 0.5 to 1 MB) on a remote database. Expected: 100 to 300 ms from Fly.io to Neon in the same region. This figure goes into the API tests as soon as the API exists, and the 500 ms budget covers both parts.

Comparison at the required size (nominal): Gale-Shapley 62.9% 1st wishes, 17.8% unassigned, average rank 1.39, 0 blocking pairs; Boston 68.9%, 18.5%, 1.25, **116 blocking pairs**. The five other scenarios, the variant with per-university weights and the 68 checks are in the report.

## 11. Tests, CI/CD, operations

**Tests** (`pytest`, one command):
- engine and generator: `packages/*/tests`, 23 tests, < 3 s: rules (validation, thresholds, bonuses, criterion without code, tie-break, overrides), two algorithms with automatic stability check, generator (reproducibility, bounds, continents), English scale, golden hashes;
- API (`TestClient`, ephemeral Postgres): permissions and cross-access, run → publish → result cycle, identical replay, database → engine mapping, end-to-end measurement;
- data: `data/universities.json` validated by a JSON schema (100 entries, 6 continents, GPS, each photo with `author`/`license`/`alt`, `cost_of_living.source`, non-empty `sources[]`);
- the benchmark (`pnpm bench`) is an assertion suite and runs in CI on every PR, report as an artifact (the report is not committed: timings vary, only the checks are comparable).

**CI** (GitHub Actions, every PR): `ruff check` + `ruff format --check`, `pytest`, benchmark, `docker build`. Required checks on `main`.

**CD**: merge to `main` → Fly.io deployment; `alembic upgrade head` at startup; demo dataset seeded if the database is empty. The SPA is built in the image and served by the API under `/` (the API under `/api`). Mobile: APK / simulator build published as an artifact by the pipeline of the mobile repository (or of the same repository, open question §14).

**Local startup**: `docker compose up` starts Postgres + API, applies the migrations, loads 100 universities and 1,000 students (`generate(seed=42)`), creates one admin account and three demo student accounts (passwords in `.env.example`). Swagger at `http://localhost:8000/docs`.

**Logs**: readable in development (SQL queries displayed), JSON in production.

## 12. The backend's place in the monorepo

```
apps/api/
├── app/
│   ├── main.py            FastAPI: routes under /api, security headers, startup (tables + demo dataset)
│   ├── db.py              SQLAlchemy connection and the tables from §4
│   ├── auth.py            argon2id, opaque sessions, require_role, login failure limiting
│   └── services.py        database → engine mapping, snapshot (including lottery) → engine → persistence
├── tests/                 functional/ (in-process API), e2e/ (running platform): see testing.md
└── Dockerfile             production image, built from the repository root
packages/engine/
├── rules/                 configuration format, criteria, thresholds, bonuses, tie-break; english.py (CEFR scale)
├── algorithms/            problem.py (shared preprocessing), gale_shapley.py, boston.py, stability.py, metrics.py
├── benchmark/run.py       benchmark: time for 1,000 students and more, per algorithm
└── tests/
packages/generator/        fictional students and universities, seed, stress scenarios; tests/
docs/technical/            this document, benchmark-protocol.md, benchmark-results.md, testing.md
docs/adr/                  decisions
pyproject.toml · uv.lock   the repository's single Python environment (uv), imported as app, engine, generator
```

Coming to `apps/api` when the need arises: Alembic (migrations), `notify.py` (FCM adapter), splitting
`main.py` into routers per area. `data/destinations/` will replace the generated universities.

## 13. Deliberately postponed

| Not done | Why | When to add it |
|---|---|---|
| Task queue (Celery, Redis) | run ≈ 16 ms; publication as a FastAPI background task (one FCM call) | if a run exceeds 5 s (≥ 100,000 students) |
| JWT / OAuth | revocable opaque sessions, simpler | never for this project |
| Redis cache for the catalog | 100 rows, `ETag` is enough | never for this project |
| Optimistic lock on wishes | one student, conflict unlikely | `If-Match` if conflicts are observed |
| History of student changes | the run snapshot is enough for replay | if individual audit is requested |
| Second round for unassigned students (≈ 18% in nominal) | policy to be decided (§14) | as soon as there is an answer: new run on the remaining seats with additional wishes, same engine |
| CEFR table editable by the admin | sourced constant (ADR-0007) | if another certification (Cambridge, TOEFL) enters the catalog |

## 14. Decisions made by the author, and questions left to the owner

**Decided here (open to challenge if needed)**: Python/FastAPI/PostgreSQL stack (ADR-0001, confirmed on 2026-11-02); common English scale by CEFR bands (ADR-0007); seeded lottery as the final tie-break; `name` excluded from the version hash; idempotent `POST /admin/configs`; exactly 5 wishes; latest published run is authoritative; publication of a Boston run rejected; cohort regeneration forbidden after a run; SPA served by the API; Fly.io rather than Render.

**To be decided by the team, because the answer changes what gets built**:
1. A single repository (web + backend + mobile, as the PDF suggests) or three: changes CI, Compose, README, GitHub Projects.
2. Mobile platform: iOS or Android. iOS ⇒ no push on the simulator, notification demo on a real device or through the fallback.
3. Fate of unassigned students: final status, second round on the remaining seats, or forced assignment?
4. Tie-break: does the seeded lottery suit the fictional school, or does it prefer a displayed deterministic criterion (seniority, etc.)?
