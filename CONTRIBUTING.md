# Contribuer

## Mise en place (une fois par clone)

Prérequis : Git, Docker, [uv](https://docs.astral.sh/uv/) et [pre-commit](https://pre-commit.com/) (`uv tool install pre-commit`).

```bash
pre-commit install            # installe les hooks pre-commit ET commit-msg
cd backend && uv sync         # dépendances verrouillées (uv.lock), Python 3.12 téléchargé si absent
uv run pytest                 # tous les tests du backend
```

## Hooks

À chaque `git commit`, sur les fichiers modifiés :

| Hook | Rôle |
|---|---|
| `trailing-whitespace`, `end-of-file-fixer` | fichiers propres, diffs sans bruit |
| `check-yaml`, `check-toml`, `check-merge-conflict` | pas de configuration cassée ni de marqueur de conflit oublié |
| `check-added-large-files` | pas de binaire lourd dans l'historique |
| `detect-private-key` | aucun secret dans le dépôt (exigence du sujet) |
| `ruff-check`, `ruff-format` | lint et format Python, corrigés automatiquement |
| `conventional-pre-commit` (étape `commit-msg`) | message conforme à Conventional Commits |

Un hook qui corrige un fichier fait échouer le commit : relire la correction, `git add`, recommiter.
La CI rejoue les mêmes hooks, en même version : contourner un hook en local (`--no-verify`) ne fait que repousser
l'échec à la PR.

## Convention de commits : [Conventional Commits 1.0.0](https://www.conventionalcommits.org/fr/v1.0.0/)

```
<type>(<portée facultative>): <description à l'impératif, en anglais>

[corps facultatif : le pourquoi]

[pied facultatif : Closes #12, BREAKING CHANGE: …]
```

| Type | Usage | Effet sur la version |
|---|---|---|
| `feat` | nouvelle fonctionnalité | mineure |
| `fix` | correction de bug | correctif |
| `docs` | documentation seule | – |
| `test` | ajout ou correction de tests | – |
| `refactor` | restructuration sans changement de comportement | – |
| `perf` | amélioration de performance | correctif |
| `style` | format, sans changement de code | – |
| `build` | dépendances, Docker, outillage de build | – |
| `ci` | pipelines GitHub Actions | – |
| `chore` | maintenance qui n'entre dans aucun autre type | – |
| `revert` | annulation d'un commit | selon le commit annulé |

Portées usuelles : `api`, `engine`, `web`, `mobile`, `data`, `docs`. Un `!` après le type (`feat(api)!: …`) signale
un changement incompatible (version majeure).

Exemples : `feat(api): add wishes endpoint`, `fix(engine): keep cutoff when capacity is zero`,
`docs: describe the test strategy`.

**Pourquoi cette convention.** Le sujet demande une convention de commits commune. Celle-ci rend l'historique lisible
(qui a fait quoi, de quelle nature), et le type de chaque commit détermine la prochaine version sémantique et le
`CHANGELOG.md`, sans débat.

**Où elle est vérifiée.** En local par le hook `commit-msg` ; en CI (`.github/workflows/conventions.yml`) sur chaque
commit de la PR **et sur le titre de la PR**, puisqu'il devient le message du commit de squash sur `main`.

## Branches et pull requests

- `main` est protégée : pas de push direct, une PR relue et une CI verte pour merger.
- Une branche par issue, nommée `<type>/<sujet-court>` : `feature/wishes-endpoint`, `fix/cutoff-zero-capacity`,
  `docs/test-strategy`.
- La PR est reliée à son issue (`Closes #12` dans la description), relue par au moins un autre membre, mergée en
  **squash** : un commit par PR sur `main`, au titre conforme à la convention.
- Versions taguées en semver aux étapes clés (`v0.1.0` au follow-up de décembre, `v1.0.0` à la soutenance).

### Vérifications obligatoires (à cocher dans *Settings → Branches → main*)

| Workflow | Job |
|---|---|
| Conventions | `Conventional Commits`, `Pre-commit hooks (lint, format, secrets)` |
| Backend | `Unit + functional tests`, `End-to-end (Docker image + PostgreSQL)`, `Engine benchmark (68 checks)` |
