# Contributing

## Setup (once per clone)

Prerequisites: Git, Docker, Node 20+ with [pnpm](https://pnpm.io/), [uv](https://docs.astral.sh/uv/) and
[pre-commit](https://pre-commit.com/) (`uv tool install pre-commit`).

```bash
pre-commit install            # installs the pre-commit AND commit-msg hooks
uv sync                       # locked Python dependencies (uv.lock), Python 3.12 downloaded if missing
pnpm test                     # all tests (or: uv run pytest)
```

## Hooks

On every `git commit`, on the changed files:

| Hook | Role |
|---|---|
| `trailing-whitespace`, `end-of-file-fixer` | clean files, diffs without noise |
| `check-yaml`, `check-toml`, `check-merge-conflict` | no broken configuration or forgotten conflict marker |
| `check-added-large-files` | no heavy binaries in the history |
| `detect-private-key` | no secrets in the repository (brief requirement) |
| `ruff-check`, `ruff-format` | Python lint and format, fixed automatically |
| `conventional-pre-commit` (`commit-msg` stage) | message conforming to Conventional Commits |

A hook that fixes a file makes the commit fail: review the fix, `git add`, commit again.
CI replays the same hooks, at the same versions: bypassing a hook locally (`--no-verify`) only postpones
the failure to the PR.

## Commit convention: [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)

```
<type>(<optional scope>): <description in the imperative, in English>

[optional body: the why]

[optional footer: Closes #12, BREAKING CHANGE: …]
```

| Type | Usage | Effect on the version |
|---|---|---|
| `feat` | new feature | minor |
| `fix` | bug fix | patch |
| `docs` | documentation only | – |
| `test` | adding or fixing tests | – |
| `refactor` | restructuring without behavior change | – |
| `perf` | performance improvement | patch |
| `style` | formatting, no code change | – |
| `build` | dependencies, Docker, build tooling | – |
| `ci` | GitHub Actions pipelines | – |
| `chore` | maintenance that fits no other type | – |
| `revert` | reverting a commit | depends on the reverted commit |

Common scopes: `api`, `engine`, `web`, `mobile`, `data`, `docs`. A `!` after the type (`feat(api)!: …`) signals
a breaking change (major version).

Examples: `feat(api): add wishes endpoint`, `fix(engine): keep cutoff when capacity is zero`,
`docs: describe the test strategy`.

**Why this convention.** The project brief asks for a shared commit convention. This one keeps the history readable
(who did what, of what kind), and the type of each commit determines the next semantic version and the
`CHANGELOG.md`, with no debate.

**Where it is checked.** Locally by the `commit-msg` hook; in CI (`.github/workflows/ci.yml`) on every
commit of the PR **and on the PR title**, since it becomes the message of the squash commit on `main`.

## Branches and pull requests

- `main` is protected: no direct push, a reviewed PR and a green CI to merge.
- One branch per issue, named `<type>/<short-topic>`: `feature/wishes-endpoint`, `fix/cutoff-zero-capacity`,
  `docs/test-strategy`.
- The PR is linked to its issue (`Closes #12` in the description), reviewed by at least one other member, merged with
  **squash**: one commit per PR on `main`, with a title that follows the convention.
- Versions tagged in semver at key milestones (`v0.1.0` at the December follow-up, `v1.0.0` at the final defense).

### Required checks (to tick in *Settings → Branches → main*)

All jobs of `.github/workflows/ci.yml`: `Conventional Commits`, `Lint (pre-commit hooks)`,
`Unit + functional tests`, `Build + end-to-end (Docker, PostgreSQL)`, `Engine benchmark (68 checks)`.

## Adding an assignment criterion

No code to change: a criterion is data, interpreted by `packages/engine/rules`.

1. Give each student the value in their `attributes` (e.g. `{"absences": 3}`); for a threshold specific to a
   university, in the university's `attributes` (e.g. `{"min_associative": 40}`).
2. Create a new configuration version (`POST /api/admin/configs`) that uses it: weight in
   `criteria`, threshold in `eliminatory`, points in `bonuses`, or tie-break in `tie_break`. A key unknown to the
   data is rejected with the list of available keys.
3. Start a run with this version (`POST /api/admin/runs`).

Full format and annotated example: [`docs/technical/architecture.md` §5](docs/technical/architecture.md).
The test `test_new_criterion_without_code_changes_outcome` (`packages/engine/tests`) shows the principle.
