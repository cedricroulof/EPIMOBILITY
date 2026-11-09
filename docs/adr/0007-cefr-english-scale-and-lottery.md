# ADR-0007 — Common English scale by CEFR bands; seeded lottery as the final tie-break

Status: accepted (author's choice, open to challenge) · Date: 2026-10-26

## Context
Students present a TOEIC (10–990) or an IELTS (0–9). The first version normalized each test on its raw scale: a TOEIC 945 was worth 95 points, an IELTS 7.0 was worth 78, even though both certify the start of level C1. Unfair, and hard to defend in front of a jury. In addition, with equal scores and tie-breaks, the engine decided by identifier: deterministic but arbitrary and invisible.

## Decision
- `english_pct` = position on a common scale where each CEFR band covers the same range (A1 = 0, A2 = 20, B1 = 40, B2 = 60, C1 = 80, top = 100), linearly interpolated within the band, based on the official tables (ETS "Mapping the TOEIC tests on the CEFR"; "IELTS and the CEFR"). TOEIC L&R does not certify C2: its maximum is worth 100 points but stays labeled C1. Code: `engine/english.py`; test: `test_english_scale_is_equitable_between_tests`.
- Tie-break: one `lottery` number per student, drawn at snapshot time with `run.seed` in id order (`generator.draw_lottery`), stored in `attributes` and therefore in the snapshot, referenced by `tie_break` and shown in the explanation. The id remains the theoretical last-resort fallback.

## Consequences
- `+` Fairness between tests; sourced and documented table; another certification is added with one line in `english.py`.
- `+` Exact ties settled in a defensible, reproducible (stored seed) and transparent (visible to the student) way.
- `−` Changing the table changes the scores and therefore the assignments: increment `ENGINE_VERSION`, update the golden hashes.
- The owner may prefer a displayed deterministic criterion to the lottery: it is one more `tie_break` entry, nothing else changes.
