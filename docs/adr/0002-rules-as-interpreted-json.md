# ADR-0002 — Rules engine: interpreted JSON configuration, no DSL or plugins

Status: accepted · Date: 2026-10-26

## Context
The administration must be able to adjust weights, eliminatory thresholds, bonuses and tie-breaks, and **add a criterion without a developer**. Configurations must be versioned and replayable.

## Options
1. **Interpreted declarative JSON**: `criteria`, `eliminatory`, `bonuses`, `tie_break` lists with allowlisted operators; new criteria read `Student.attributes`.
2. **Expression mini-language** (e.g. `gpa * 0.5 + (english > 800 ? 10 : 0)`): more expressive, but a parser to write, test, secure and document.
3. **Python plugins** loaded dynamically: "without modifying the code" becomes false, and it is arbitrary code execution.

## Decision
Option 1. One criterion = one JSON entry; the normalization `(value − min)/(max − min)` makes weights comparable; `default` handles missing attributes; `validate` returns all errors at once.

## Consequences
- `+` No `eval`, zero attack surface (A03); admin form trivial to generate from the schema; content hash = version identifier.
- `+` Proven: the benchmark adds a bonus and a penalty through configuration alone and gets a different assignment that is still stable.
- `−` No arbitrary combinations (product of criteria, nested conditions). If a real need appears, add an operator or a rule type, not a language.
- `overrides` per university (criteria and/or bonuses): planned from the start, with no algorithm change; thresholds can target an attribute added on the university side (`University.attributes`).
- `validate` receives the keys actually present in the data: an unknown key (typo, attribute never filled in) is rejected before the run.
