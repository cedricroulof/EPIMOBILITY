# EPIMOBILITY

[![CI](https://github.com/cedricroulof/EPIMOBILITY/actions/workflows/ci.yml/badge.svg)](https://github.com/cedricroulof/EPIMOBILITY/actions/workflows/ci.yml)

EPIMOBILITY is an educational project with fictive partnership, neither the school or its affiliate are real.

> **Educational project: fictional partnerships.**

International mobility platform: assign 1,000 students to 100 universities according to their wishes, their profile
and rules configurable by the administration.

## Getting started

Prerequisites: Docker.

```bash
docker compose up --build       # or: pnpm dev
```

The API starts at <http://localhost:8000/api> with a demo dataset (100 universities, 1,000 generated students,
seed 42). Interactive API documentation: <http://localhost:8000/docs>.

| Demo account | Password | Role |
|---|---|---|
| `admin@exemple.test` | `demo1234` | admin |
| `etudiant1@exemple.test` … `etudiant3@exemple.test` | `demo1234` | student |

Default values can be overridden in a `.env` file (see `.env.example`).

## Tests and lint

Prerequisites: [uv](https://docs.astral.sh/uv/) and [pnpm](https://pnpm.io/).

```bash
pnpm test     # unit, functional and end-to-end, ≈ 15 s (or: uv run pytest)
pnpm lint     # pre-commit hooks on the whole repository
pnpm bench    # algorithm benchmark
```

Strategy and rationale for each test level: [`docs/technical/testing.md`](docs/technical/testing.md).

## Repository layout

```
apps/
  api/                  Python REST API (FastAPI): auth, roles, catalogue, wishes, runs, publication, replay
packages/
  engine/               pure engine, no I/O: rules/, algorithms/ (Gale-Shapley, Boston, stability), benchmark/
  generator/            reproducible fictional students and universities (seed), stress scenarios
docs/
  technical/            architecture, data model, API, algorithm comparison, test strategy
  adr/                  one decision per file
.github/                ci.yml, issue and pull request templates
docker-compose.yml      database + API in one command
pyproject.toml, uv.lock locked Python environment; package.json, pnpm-lock.yaml: repository scripts
```

`apps/web`, `apps/mobile`, `packages/shared`, `data/` and `docs/user`, `docs/accessibility`, `docs/brand` will arrive
with their respective parts of the project.

## Documentation

- [Architecture](docs/technical/architecture.md) and [decisions (ADR)](docs/adr/)
- [Algorithm comparison](docs/technical/benchmark-results.md)
- [Contributing: hooks, commit convention, branches, adding a criterion](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md) · [Code of conduct](CODE_OF_CONDUCT.md) · [MIT License](LICENSE)

## AI usage

| Tool | Usage |
|---|---|
| Claude (Anthropic) | backend: help with design, API and engine code, tests, CI and documentation; all code is reviewed in pull requests and explained by the team |
