# Changelog

Notable changes to this project are recorded here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions: [semver](https://semver.org/).

## [Unreleased]

### Added

- Monorepo: `apps/`, `packages/`, `docs/`, scripts `pnpm dev`, `pnpm test`, `pnpm lint`, `pnpm bench`.
- Pre-commit hooks (format, lint, secrets) and Conventional Commits check, locally and in CI.
- Matching engine (`packages/engine`): JSON rules configurable without code, Gale-Shapley and Boston,
  automatic stability check, per-wish explanations, benchmark.
- Reproducible generator of fictional students and stress scenarios (`packages/generator`).
- Proof-of-concept API (`apps/api`): cookie and Bearer sessions, student and admin roles, catalogue, wishes,
  versioned configurations, runs, publication, explained result, replay, what-if comparison.
- Unit, functional and end-to-end tests; CI (`ci.yml`) with Docker build and PostgreSQL.
- Docker Compose: database and API in one command, demo dataset loaded at startup.
- CI: dependency licence check and secret scan across the full history; Dependabot.
- Ruff: PEP 8 rules completed (`W`, `N`) and line length checked at 120 characters.
