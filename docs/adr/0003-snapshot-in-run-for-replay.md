# ADR-0003 — Replay: the run stores a full snapshot of its inputs

Status: accepted · Date: 2026-10-26

## Context
"It must be possible to replay an assignment identically." Between two runs, wishes change, capacities are corrected, attributes are added. A configuration alone is not enough to replay.

## Options
1. **JSONB snapshot in `runs.input_snapshot`**: students (fields + attributes + wishes) and universities (capacity, thresholds) as they were. Plus `input_hash` and `output_hash`.
2. **Version every entity** (history tables, `valid_from/valid_to`) and rebuild the state as of the run date: exact but heavy, and fragile if a migration forgets a table.
3. **Event sourcing**: out of proportion.

## Decision
Option 1. Measured: 160 KB per 1,000 × 100 snapshot; one hundred runs = 16 MB. The replay reads back the snapshot and the immutable configuration, reruns the engine, compares `output_hash` and responds with `identical: true|false`.

## Consequences
- `+` Replay independent of the current database state, proven by the benchmark (same snapshot + same config ⇒ same hash; shuffled inputs ⇒ same hash).
- `+` A run is self-contained: exportable, auditable, comparable.
- `−` Data duplication between runs (accepted, low volumes). Snapshots of unpublished runs older than 6 months can be purged if necessary.
- Configurations are immutable in the database (`rule_configs` without `UPDATE`): without this, the snapshot would not be enough.
