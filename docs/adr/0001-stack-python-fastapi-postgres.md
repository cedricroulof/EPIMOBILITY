# ADR-0001 — Stack backend : Python 3.12, FastAPI, PostgreSQL

Statut : accepté (confirmé le 2026-11-02) · Date : 2026-10-26

## Contexte
Stack libre, à justifier. Le sujet exige : une référence d'API OpenAPI, un moteur de règles et d'affectation testé et mesuré, une installation en une commande, un nouveau contributeur opérationnel en 15 minutes, un déploiement continu sur offre gratuite. Groupe de 3 : un backend, un web, un mobile.

## Options
1. **Python + FastAPI + SQLAlchemy + PostgreSQL** — OpenAPI et validation gratuits (Pydantic), moteur en bibliothèque standard, peu de code.
2. **TypeScript + NestJS (ou Fastify) + Prisma + PostgreSQL** — un seul langage si le web est en React et le mobile en React Native ; plus de code pour le même résultat, OpenAPI via décorateurs.
3. **Go + chi/echo + sqlc** — plus rapide à l'exécution, mais la performance n'est pas la contrainte (run ≈ 15 ms en Python) ; OpenAPI à maintenir à la main ou par génération de code.

## Décision
Option 1. Le moteur (`packages/engine`) n'a aucune dépendance et a été benchmarké tel quel ; FastAPI fournit la documentation d'API exigée sans travail ; PostgreSQL apporte JSONB (configurations, snapshots, attributs libres) et les contraintes d'intégrité.

## Conséquences
- `+` OpenAPI toujours synchronisée avec le code ; validation aux frontières déclarative ; tests sans base pour le moteur.
- `+` Lecture facile pour un relecteur non-Python (pas de métaprogrammation).
- `−` Pas de partage de types avec un front TypeScript : générer le client depuis `openapi.json` (`openapi-typescript`, `openapi-generator` pour Kotlin/Swift/Dart).
- Si l'équipe préfère l'option 2 : l'architecture (modèle de données, API, cycle de run, moteur) se transpose à l'identique ; le protocole de benchmark et le vérificateur de stabilité servent d'oracle pour valider le portage.
