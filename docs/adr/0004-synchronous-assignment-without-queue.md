# ADR-0004 — The run executes inside the HTTP request, without a task queue

Status: accepted · Date: 2026-10-26

## Context
The reflex for "launching a simulation" is a worker (Celery, RQ) and a queue (Redis), with a status to poll. This adds two services to Docker Compose, one more deployment, and intermediate states to handle in the UIs.

## Measurement
Benchmark (`docs/technical/benchmark-results.md`): preparation + assignment + stability check for 1,000 × 100 ≈ 16 ms; 10,000 × 1,000 ≈ 0.2 s; 50,000 × 1,000 ≈ 1.1 s. Fixed budget: 500 ms, which must also cover the database (reading the cohort, writing the snapshot and the 1,000 assignments: to be measured as soon as the API exists, expected 100 to 300 ms).

## Decision
`POST /admin/runs` computes and persists within the request, and responds `201` with the full run. The 1,000 assignments are persisted in a single multi-row `INSERT` in the same transaction.

Exception: **publication** notifies the cohort. Calling one thousand FCM tokens one by one within the request would be unacceptable; the API subscribes each device to the FCM topic `results` at registration and sends **a single** topic message, as a FastAPI `BackgroundTask` so as not to tie the response to FCM availability.

## Consequences
- `+` One service, one deployment, zero "in progress" state; what-if mode is instantaneous.
- `+` Engine error ⇒ transaction rolled back, `status = failed`, message reported to the admin.
- `−` Ceiling: beyond ≈ 10,000 students × 1,000 universities (ten times the required size), the computation alone approaches the budget; at that point, move to a `BackgroundTask`, then to a queue. The `runs.py` service is the only place to change.
