"""Matching engine: pure module (no I/O, no dependencies), testable and benchmarkable without a database.

rules/       → interpreted JSON configuration: weights, eliminatory thresholds, bonuses, tie-break;
               english.py: common English scale (CEFR bands), with its sources
algorithms/  → Gale-Shapley and Boston on shared preprocessing, stability check, comparison, explanations
benchmark/   → benchmark: per-algorithm times from 1,000 to 50,000 students, 68 checks
Input data (universities, fictional students, seed) comes from `packages/generator`.

ENGINE_VERSION is stored in each run: a replay with `identical: false` after an engine update is explained by this
field.
"""

ENGINE_VERSION = "1.0.0"
