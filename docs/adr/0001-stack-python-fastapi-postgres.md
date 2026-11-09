# ADR-0001 — Backend stack: Python 3.12, FastAPI, PostgreSQL

Status: accepted (confirmed on 2026-11-02) · Date: 2026-10-26

## Context
Free choice of stack, to be justified. The project brief requires: an OpenAPI API reference, a tested and measured rules and matching engine, one-command installation, a new contributor up and running in 15 minutes, continuous deployment on a free tier. Team of 3: one backend, one web, one mobile.

## Options
1. **Python + FastAPI + SQLAlchemy + PostgreSQL** — OpenAPI and validation for free (Pydantic), standard-library engine, little code.
2. **TypeScript + NestJS (or Fastify) + Prisma + PostgreSQL** — a single language if the web app is in React and the mobile app in React Native; more code for the same result, OpenAPI through decorators.
3. **Go + chi/echo + sqlc** — faster at runtime, but performance is not the constraint (run ≈ 15 ms in Python); OpenAPI to maintain by hand or through code generation.

## Decision
Option 1. The engine (`packages/engine`) has no dependencies and was benchmarked as is; FastAPI provides the required API documentation with no extra work; PostgreSQL brings JSONB (configurations, snapshots, free-form attributes) and integrity constraints.

## Consequences
- `+` OpenAPI always in sync with the code; declarative validation at the boundaries; engine tests without a database.
- `+` Easy to read for a non-Python reviewer (no metaprogramming).
- `−` No type sharing with a TypeScript front end: generate the client from `openapi.json` (`openapi-typescript`, `openapi-generator` for Kotlin/Swift/Dart).
- If the team prefers option 2: the architecture (data model, API, run lifecycle, engine) carries over unchanged; the benchmark protocol and the stability checker serve as an oracle to validate the port.
