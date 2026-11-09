# ADR-0006 — Second algorithm: Boston mechanism (immediate acceptance)

Status: accepted · Date: 2026-10-26

## Context
"At least 2 algorithms, including a stable marriage (Gale-Shapley). Quantified comparison: % of first wishes, % of unassigned students, average rank, stability." The second one must make the comparison instructive.

## Options
1. **Boston (immediate acceptance)**: wish 1 for everyone, final admissions, then wish 2 on the remaining seats, etc. This is the "intuitive" algorithm that many schools apply by hand.
2. **Serial dictatorship by score**: students are served in descending score order, each one takes their best available wish. Without per-university weights, the score is the same for every university and this algorithm gives exactly the same result as Gale-Shapley: an empty comparison. (With `overrides`, the rankings differ and Gale-Shapley becomes distinct again; stability is then a non-trivial property, shown by the "nominal + overrides" row of the benchmark.)
3. **University-proposing Gale-Shapley**: same result as student-proposing when priorities are shared; different with `overrides`, but optimal for universities, which is not the goal.

## Decision
Option 1. Boston mechanically maximizes the number of first wishes (optimum reached university by university) but produces blocking pairs and encourages lying about one's first wish. The comparison shows the real trade-off: +6 points of first wishes against 116 blocking pairs on the nominal scenario, +9 points against 250 pairs on the reduced-capacity scenario.

## Consequences
- `+` The stability checker has something to detect (the benchmark requires it to find pairs on Boston: a test of the test).
- `+` Both algorithms share the same preprocessing (`Problem`): comparison under equal conditions.
- Gale-Shapley remains the publication algorithm; Boston is shown in what-if mode with its warning, and `POST /admin/runs/{id}/publish` rejects a Boston run (`409`).
