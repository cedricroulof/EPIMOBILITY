# Matching engine benchmark protocol

Goal: prove, reproducibly, that the engine is **correct** (invariants, stability, consistent explanations, replay) and **robust** (stress scenarios, scaling), and measure the computation time required by the project brief.

## Running

```
pnpm bench                        # ≈ 10 s, writes docs/technical/benchmark-results.md, exit code 1 if a check fails
uv run pytest packages            # engine and generator unit tests, < 1 s
```

The engine has no dependencies. The benchmark runs in CI on every PR, with the report as an artifact (without committing it: times vary from one machine to another, only the checks and the assignment metrics are comparable).

## Dataset

`packages/generator`, seed 42, 1,000 students × 100 universities. Synthetic but consistent universities: a selectivity drawn from Beta(2, 3) simultaneously drives the seats (3 to 17), the minimum GPA (2.0 to 3.5), the minimum English level (B1 / B2 / C1) and the popularity. Students: GPA ~ N(2.9; 0.5) clamped to [1; 4], TOEIC ~ N(720; 150) (60%) or IELTS ~ N(6.3; 1.0) (40%), associative activity ~ N(50; 20), 5 distinct wishes drawn by popularity with self-selection (an ineligible wish is kept only 15% of the time, "dream wish"). A `lottery` number is drawn with seed 42, as the API will do at snapshot time.

| Scenario | What it tests |
|---|---|
| `nominal` | realistic distributions, total capacity ≈ 1.1 × headcount |
| `oversubscribed` | 60% of students concentrate their wishes on the 10 most popular universities |
| `weak_english` | cohort weak in English: many ineligible students, high share of unassigned students |
| `tight_capacity` | capacities reduced to 80%: fewer seats than students |
| `abundant` | capacities tripled: the two algorithms must converge |
| `ties` | all profiles identical: only the seeded lottery decides; the result must stay stable and deterministic |
| `nominal + overrides` | nominal data, but the 15 most contested universities weight English at 60%: rankings differ from one university to another |

## Metrics (per scenario and per algorithm)

- **1st wish**: % of students assigned to their wish 1 · **Unassigned**: % without a seat · **Average rank**: among assigned students · **Rank distribution**.
- **Blocking pairs**: number of (student, university) pairs such that the student prefers the university to their assignment and the university has a free seat or prefers the student to its worst admitted student. 0 ⇔ stable. Computed independently of the algorithms (`metrics.blocking_pairs`).
- **Fill rate**: assigned / seats.
- **Time**: preparation (scores, eligibility, sorting of applicants), assignment, blocking pair detection alone; median of 5 executions (a single one above 1,000 students), `time.perf_counter`.

## Correctness checks (the benchmark fails if one breaks)

| Category | Check |
|---|---|
| Invariants | assigned only to one of their wishes; never where ineligible; never over capacity (every scenario, every algorithm) |
| Overrides | with per-university weights, Gale-Shapley stays stable and the result differs from the case without an override |
| Stability | Gale-Shapley: 0 blocking pairs on every scenario and at scales 10,000 × 1,000 and 50,000 × 1,000; the detector finds pairs on Boston (test of the test) |
| Theoretical property | Boston serves at least as many 1st wishes as Gale-Shapley on every scenario |
| Explanations | every "rejected" has a score ≤ stated cutoff; every "admitted" has a score ≥ cutoff; with Gale-Shapley, a rejection without a cutoff only exists for zero capacity |
| Generator | same seed ⇒ same hash; different seed ⇒ different hash; 6 continents; 5 distinct valid wishes |
| Replay | same snapshot + same configuration ⇒ same assignment hash (both algorithms) |
| Determinism | shuffled input rows ⇒ same hash (both algorithms) |
| Versioning | changing a weight ⇒ new configuration id and different assignments |
| Rules without code | adding a bonus and a penalty through configuration alone ⇒ assignment changed, still stable |
| Validation | an invalid configuration is rejected with all its errors (types, operators, unknown keys, CEFR level); a CEFR threshold as a constant ("C1") is accepted and applied |
| Budget | preparation + assignment + check < 500 ms for 1,000 × 100 |
| Storage | input snapshot < 1 MB |

## Adding a scenario

One entry in `generator.SCENARIOS` and, if needed, a branch in `generator.generate`. The benchmark and the tests run it automatically.

## Known limitations

- Synthetic universities: the 100 real ones will replace `make_universities` with loading from `data/universities.json`; the rest of the protocol is unchanged.
- Times measured without the database: the end-to-end measurement (`POST /admin/runs`) will be added to the API tests.
- Reference machine: Apple M3; CI times will be 2 to 4 times slower, the 500 ms budget leaves a 10× margin on the computation alone.
- Synthetic universities: the most selective ones receive few eligible applicants (self-selection), the stress falls on the mid-range universities; this is why the `overrides` variant targets the most contested universities and not the most selective ones.
