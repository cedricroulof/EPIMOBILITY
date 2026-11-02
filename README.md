# EPIMOBILITY

[![CI](https://github.com/cedricroulof/EPIMOBILITY/actions/workflows/ci.yml/badge.svg)](https://github.com/cedricroulof/EPIMOBILITY/actions/workflows/ci.yml)

EPIMOBILITY is an educational project with fictive partnership, neither the school or its affiliate are real.

> **Projet pédagogique : partenariats fictifs.**

Plateforme de mobilité internationale : répartir 1 000 étudiants sur 100 universités selon leurs vœux, leur profil
et des règles configurables par l'administration.

## Démarrage

Prérequis : Docker.

```bash
docker compose up --build       # ou : pnpm dev
```

L'API démarre sur <http://localhost:8000/api> avec un jeu de démo (100 universités, 1 000 étudiants générés,
seed 42). Documentation interactive de l'API : <http://localhost:8000/docs>.

| Compte de démo | Mot de passe | Rôle |
|---|---|---|
| `admin@exemple.test` | `demo1234` | administration |
| `etudiant1@exemple.test` … `etudiant3@exemple.test` | `demo1234` | étudiant |

Valeurs par défaut surchargeables dans un fichier `.env` (voir `.env.example`).

## Tests et lint

Prérequis : [uv](https://docs.astral.sh/uv/) et [pnpm](https://pnpm.io/).

```bash
pnpm test     # unitaires, fonctionnels et end-to-end, ≈ 15 s (ou : uv run pytest)
pnpm lint     # hooks pre-commit sur tout le dépôt
pnpm bench    # banc d'essai des algorithmes
```

Stratégie et justification de chaque niveau de test : [`docs/technical/testing.md`](docs/technical/testing.md).

## Arborescence

```
apps/
  api/                  API REST Python (FastAPI) : auth, rôles, catalogue, vœux, runs, publication, rejeu
packages/
  engine/               moteur pur, sans I/O : rules/, algorithms/ (Gale-Shapley, Boston, stabilité), benchmark/
  generator/            étudiants et universités fictifs reproductibles (seed), scénarios de tension
docs/
  technical/            architecture, modèle de données, API, comparatif des algorithmes, stratégie de tests
  adr/                  une décision par fichier
.github/                ci.yml, modèles d'issue et de pull request
docker-compose.yml      base + API en une commande
pyproject.toml, uv.lock environnement Python verrouillé ; package.json, pnpm-lock.yaml : scripts du dépôt
```

`apps/web`, `apps/mobile`, `packages/shared`, `data/` et `docs/user`, `docs/accessibility`, `docs/brand` arrivent
avec leurs parties respectives.

## Documentation

- [Architecture](docs/technical/architecture.md) et [décisions (ADR)](docs/adr/)
- [Comparatif des algorithmes](docs/technical/benchmark-results.md)
- [Contribuer : hooks, convention de commits, branches, ajout d'un critère](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md) · [Code de conduite](CODE_OF_CONDUCT.md) · [Licence MIT](LICENSE)

## Usage de l'IA

| Outil | Usage |
|---|---|
| Claude (Anthropic) | backend : aide à la conception, au code de l'API et du moteur, aux tests, à la CI et à la documentation ; tout le code est relu en pull request et expliqué par l'équipe |
