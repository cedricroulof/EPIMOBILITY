# Matching engine benchmark results

## 1. Comparison by scenario (1,000 students × 100 universities, seed 42)

| Scenario | Algorithm | 1st wish | Unassigned | Average rank | Blocking pairs | Fill rate | Preparation | Assignment | Blocking pair detection |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| nominal | gale_shapley | 62.9 % | 17.8 % | 1.388 | 0 | 73.7 % | 15.3 ms | 0.5 ms | 0.3 ms |
| nominal | boston | 68.9 % | 18.5 % | 1.248 | 116 | 73.1 % | 15.3 ms | 0.5 ms | 0.3 ms |
| oversubscribed | gale_shapley | 49.0 % | 20.3 % | 1.733 | 0 | 71.5 % | 14.5 ms | 0.4 ms | 0.3 ms |
| oversubscribed | boston | 53.0 % | 22.1 % | 1.601 | 76 | 69.9 % | 14.5 ms | 0.6 ms | 0.3 ms |
| weak_english | gale_shapley | 43.1 % | 34.7 % | 1.496 | 0 | 58.6 % | 14.1 ms | 0.4 ms | 0.3 ms |
| weak_english | boston | 46.2 % | 35.4 % | 1.418 | 43 | 57.9 % | 14.1 ms | 0.6 ms | 0.3 ms |
| tight_capacity | gale_shapley | 55.5 % | 27.8 % | 1.402 | 0 | 80.5 % | 15.1 ms | 0.5 ms | 0.4 ms |
| tight_capacity | boston | 64.1 % | 28.3 % | 1.16 | 250 | 79.9 % | 15.1 ms | 0.6 ms | 0.3 ms |
| abundant | gale_shapley | 71.7 % | 13.7 % | 1.257 | 0 | 25.8 % | 15.2 ms | 0.4 ms | 0.2 ms |
| abundant | boston | 71.7 % | 13.7 % | 1.257 | 0 | 25.8 % | 15.2 ms | 0.5 ms | 0.2 ms |
| ties | gale_shapley | 71.0 % | 3.2 % | 1.51 | 0 | 86.8 % | 17.5 ms | 0.6 ms | 0.3 ms |
| ties | boston | 78.4 % | 5.8 % | 1.322 | 166 | 84.5 % | 17.5 ms | 0.6 ms | 0.3 ms |
| nominal + overrides | gale_shapley | 62.6 % | 17.6 % | 1.409 | 0 | 73.9 % | 17.4 ms | 0.5 ms | 0.3 ms |
| nominal + overrides | boston | 68.9 % | 18.5 % | 1.254 | 125 | 73.1 % | 17.4 ms | 0.5 ms | 0.3 ms |

How to read this: Boston maximizes first wishes but creates blocking pairs (a student and a university that would prefer each other to their assignment). Gale-Shapley never creates any, at the cost of a few first wishes.

### Distribution of obtained ranks (nominal scenario)

| Algorithm | Wish 1 | Wish 2 | Wish 3 | Wish 4 | Wish 5 | Unassigned |
|---|---:|---:|---:|---:|---:|---:|
| gale_shapley | 629 | 113 | 45 | 24 | 11 | 178 |
| boston | 689 | 73 | 35 | 13 | 5 | 185 |

## 2. Scaling (margin beyond the requirement: 1,000 × 100)

| Students | Universities | Algorithm | Preparation | Assignment | Blocking pair detection | Total |
|---:|---:|---|---:|---:|---:|---:|
| 1 000 | 100 | gale_shapley | 15 ms | 0 ms | 0 ms | 16 ms |
| 1 000 | 100 | boston | 15 ms | 1 ms | 0 ms | 16 ms |
| 10 000 | 1 000 | gale_shapley | 175 ms | 6 ms | 3 ms | 184 ms |
| 10 000 | 1 000 | boston | 175 ms | 6 ms | 3 ms | 184 ms |
| 50 000 | 1 000 | gale_shapley | 974 ms | 62 ms | 40 ms | 1077 ms |
| 50 000 | 1 000 | boston | 974 ms | 49 ms | 40 ms | 1063 ms |

## 3. Correctness checks: 68/68 passed

- ✅ nominal/gale_shapley: invariants (wishes, eligibility, capacities)
- ✅ nominal/gale_shapley: explanations consistent with the cutoffs
- ✅ nominal/gale_shapley: 0 blocking pairs (stability) — 0
- ✅ nominal/gale_shapley: budget 500 ms (preparation + assignment + check) — 16 ms
- ✅ nominal/boston: invariants (wishes, eligibility, capacities)
- ✅ nominal/boston: explanations consistent with the cutoffs
- ✅ nominal: Boston serves at least as many 1st wishes as Gale-Shapley (theoretical property) — boston 68.9 vs GS 62.9
- ✅ oversubscribed/gale_shapley: invariants (wishes, eligibility, capacities)
- ✅ oversubscribed/gale_shapley: explanations consistent with the cutoffs
- ✅ oversubscribed/gale_shapley: 0 blocking pairs (stability) — 0
- ✅ oversubscribed/gale_shapley: budget 500 ms (preparation + assignment + check) — 15 ms
- ✅ oversubscribed/boston: invariants (wishes, eligibility, capacities)
- ✅ oversubscribed/boston: explanations consistent with the cutoffs
- ✅ oversubscribed: Boston serves at least as many 1st wishes as Gale-Shapley (theoretical property) — boston 53.0 vs GS 49.0
- ✅ weak_english/gale_shapley: invariants (wishes, eligibility, capacities)
- ✅ weak_english/gale_shapley: explanations consistent with the cutoffs
- ✅ weak_english/gale_shapley: 0 blocking pairs (stability) — 0
- ✅ weak_english/gale_shapley: budget 500 ms (preparation + assignment + check) — 15 ms
- ✅ weak_english/boston: invariants (wishes, eligibility, capacities)
- ✅ weak_english/boston: explanations consistent with the cutoffs
- ✅ weak_english: Boston serves at least as many 1st wishes as Gale-Shapley (theoretical property) — boston 46.2 vs GS 43.1
- ✅ tight_capacity/gale_shapley: invariants (wishes, eligibility, capacities)
- ✅ tight_capacity/gale_shapley: explanations consistent with the cutoffs
- ✅ tight_capacity/gale_shapley: 0 blocking pairs (stability) — 0
- ✅ tight_capacity/gale_shapley: budget 500 ms (preparation + assignment + check) — 16 ms
- ✅ tight_capacity/boston: invariants (wishes, eligibility, capacities)
- ✅ tight_capacity/boston: explanations consistent with the cutoffs
- ✅ tight_capacity: Boston serves at least as many 1st wishes as Gale-Shapley (theoretical property) — boston 64.1 vs GS 55.5
- ✅ abundant/gale_shapley: invariants (wishes, eligibility, capacities)
- ✅ abundant/gale_shapley: explanations consistent with the cutoffs
- ✅ abundant/gale_shapley: 0 blocking pairs (stability) — 0
- ✅ abundant/gale_shapley: budget 500 ms (preparation + assignment + check) — 16 ms
- ✅ abundant/boston: invariants (wishes, eligibility, capacities)
- ✅ abundant/boston: explanations consistent with the cutoffs
- ✅ abundant: Boston serves at least as many 1st wishes as Gale-Shapley (theoretical property) — boston 71.7 vs GS 71.7
- ✅ ties/gale_shapley: invariants (wishes, eligibility, capacities)
- ✅ ties/gale_shapley: explanations consistent with the cutoffs
- ✅ ties/gale_shapley: 0 blocking pairs (stability) — 0
- ✅ ties/gale_shapley: budget 500 ms (preparation + assignment + check) — 18 ms
- ✅ ties/boston: invariants (wishes, eligibility, capacities)
- ✅ ties/boston: explanations consistent with the cutoffs
- ✅ ties: Boston serves at least as many 1st wishes as Gale-Shapley (theoretical property) — boston 78.4 vs GS 71.0
- ✅ nominal + overrides/gale_shapley: invariants (wishes, eligibility, capacities)
- ✅ nominal + overrides/gale_shapley: explanations consistent with the cutoffs
- ✅ nominal + overrides/gale_shapley: 0 blocking pairs (stability) — 0
- ✅ nominal + overrides/gale_shapley: budget 500 ms (preparation + assignment + check) — 18 ms
- ✅ nominal + overrides/boston: invariants (wishes, eligibility, capacities)
- ✅ nominal + overrides/boston: explanations consistent with the cutoffs
- ✅ nominal + overrides: Boston serves at least as many 1st wishes as Gale-Shapley (theoretical property) — boston 68.9 vs GS 62.6
- ✅ The stability checker does detect instability (Boston > 0 pairs on at least one scenario)
- ✅ Per-university weights (overrides): Gale-Shapley stays stable and the ranking differs between universities
- ✅ Generator: same seed ⇒ identical dataset (hash) — 7503f5a3ac7b1319
- ✅ Generator: different seed ⇒ different dataset — 7503f5a3ac7b1319 vs 26130efa74a8e063
- ✅ Generator: the 6 inhabited continents are covered — ['Afrique', 'Amérique du Nord', 'Amérique du Sud', 'Asie', 'Europe', 'Océanie']
- ✅ Generator: 5 distinct and valid wishes for each student
- ✅ Input snapshot of a run (stored as JSONB for replay) < 1 MB — 182 KB
- ✅ Replay/gale_shapley: same snapshot + same config ⇒ identical assignment — 8d3822f1957c1f63
- ✅ Determinism/gale_shapley: shuffled input row order ⇒ same assignment
- ✅ Replay/boston: same snapshot + same config ⇒ identical assignment — 78485432471f8670
- ✅ Determinism/boston: shuffled input row order ⇒ same assignment
- ✅ Versioning: changing a weight ⇒ new configuration id — 0105de869c445535 → f6a8f6a6790fc2c7
- ✅ What-if mode: the new weights really change assignments — 101 students moved
- ✅ New criterion without code: "personal project" bonus + "absences" penalty added by config alone, assignment changed, still stable — 84 students moved
- ✅ Validation: an invalid configuration is rejected with all its errors (types, operators, unknown keys, CEFR level) — 7 errors listed
- ✅ CEFR threshold as a constant ("C1"): accepted, applied, stable assignment
- ✅ Scale 1000×100: Gale-Shapley stays stable
- ✅ Scale 10000×1000: Gale-Shapley stays stable
- ✅ Scale 50000×1000: Gale-Shapley stays stable

## Environment

- Python 3.14.5, arm64, Darwin 27.0.0
- Times: median of 5 executions (only 1 execution above 1,000 students), `time.perf_counter`; times vary from one machine and one execution to another, only the checks are comparable between two reports
- Generated by `pnpm bench` on 2026-10-26 17:26
