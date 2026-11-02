# EPIMOBILITY

[![Backend](https://github.com/cedricroulof/EPIMOBILITY/actions/workflows/backend.yml/badge.svg)](https://github.com/cedricroulof/EPIMOBILITY/actions/workflows/backend.yml)
[![Conventions](https://github.com/cedricroulof/EPIMOBILITY/actions/workflows/conventions.yml/badge.svg)](https://github.com/cedricroulof/EPIMOBILITY/actions/workflows/conventions.yml)

EPIMOBILITY is an educational project with fictive partnership, neither the school or its affiliate are real.

> **Projet pédagogique : partenariats fictifs.**

Plateforme de mobilité internationale : répartir 1 000 étudiants sur 100 universités selon leurs vœux, leur profil
et des règles configurables par l'administration.

## Démarrage

Prérequis : Docker.

```bash
docker compose up --build
```

L'API démarre sur <http://localhost:8000/api> avec un jeu de démo (100 universités, 1 000 étudiants générés,
seed 42). Documentation interactive de l'API : <http://localhost:8000/docs>.

| Compte de démo | Mot de passe | Rôle |
|---|---|---|
| `admin@exemple.test` | `demo1234` | administration |
| `etudiant1@exemple.test` … `etudiant3@exemple.test` | `demo1234` | étudiant |

Valeurs par défaut surchargeables dans un fichier `.env` (voir `.env.example`).

## Tests

Prérequis : [uv](https://docs.astral.sh/uv/).

```bash
cd backend && uv run pytest     # unitaires, fonctionnels et end-to-end, ≈ 15 s
```

Stratégie et justification de chaque niveau : [`backend/docs/testing.md`](backend/docs/testing.md).

## Arborescence

| Dossier | Contenu |
|---|---|
| `backend/app/` | API FastAPI : authentification, catalogue, vœux, configurations, runs, publication, rejeu |
| `backend/engine/` | moteur pur : règles JSON, Gale-Shapley, Boston, stabilité, explications, générateur |
| `backend/tests/` | `unit/`, `functional/`, `e2e/` |
| `backend/bench/` | banc d'essai des algorithmes |
| `backend/docs/` | architecture, ADR, protocole et résultats du banc, stratégie de tests |

## Documentation

- [Architecture du backend](backend/docs/architecture.md) et [décisions (ADR)](backend/docs/adr/)
- [Comparatif des algorithmes](backend/docs/benchmark-results.md)
- [Contribuer : hooks, convention de commits, branches](CONTRIBUTING.md)

## Usage de l'IA

| Outil | Usage |
|---|---|
| Claude (Anthropic) | backend : aide à la conception, au code de l'API et du moteur, aux tests, à la CI et à la documentation ; tout le code est relu en pull request et expliqué par l'équipe |
