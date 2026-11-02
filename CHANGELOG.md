# Changelog

Les changements notables de ce projet sont consignés ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; versions : [semver](https://semver.org/lang/fr/).

## [Unreleased]

### Added

- Mono-dépôt : `apps/`, `packages/`, `docs/`, scripts `pnpm dev`, `pnpm test`, `pnpm lint`, `pnpm bench`.
- Hooks pre-commit (format, lint, secrets) et vérification Conventional Commits, en local et en CI.
- Moteur d'affectation (`packages/engine`) : règles JSON configurables sans code, Gale-Shapley et Boston,
  vérification automatique de stabilité, explications par vœu, banc d'essai.
- Générateur reproductible d'étudiants fictifs et de scénarios de tension (`packages/generator`).
- API en preuve de concept (`apps/api`) : sessions cookie et Bearer, rôles étudiant et admin, catalogue, vœux,
  configurations versionnées, runs, publication, résultat expliqué, rejeu, comparaison « et si ».
- Tests unitaires, fonctionnels et de bout en bout ; CI (`ci.yml`) avec build Docker et PostgreSQL.
- Docker Compose : base et API en une commande, jeu de démo chargé au démarrage.
