# ADR-0003 — Rejeu : le run stocke un snapshot complet de ses entrées

Statut : accepté · Date : 2026-10-26

## Contexte
« On doit pouvoir rejouer une affectation à l'identique. » Entre deux runs, des vœux changent, des capacités sont corrigées, des attributs sont ajoutés. Une configuration seule ne suffit pas à rejouer.

## Options
1. **Snapshot JSONB dans `runs.input_snapshot`** : étudiants (champs + attributs + vœux) et universités (capacité, seuils) tels qu'ils étaient. Plus `input_hash` et `output_hash`.
2. **Versionner chaque entité** (tables d'historique, `valid_from/valid_to`) et reconstituer l'état à la date du run : exact mais lourd, et fragile si une migration oublie une table.
3. **Event sourcing** : hors de proportion.

## Décision
Option 1. Mesuré : 160 Ko par snapshot de 1 000 × 100 ; cent runs = 16 Mo. Le rejeu relit le snapshot et la configuration immuable, relance le moteur, compare `output_hash` et répond `identical: true|false`.

## Conséquences
- `+` Rejeu indépendant de l'état courant de la base, prouvé par le banc (même snapshot + même config ⇒ même hash ; entrées mélangées ⇒ même hash).
- `+` Un run est auto-suffisant : exportable, auditable, comparable.
- `−` Duplication de données entre runs (acceptée, volumes faibles). Purge possible des snapshots des runs non publiés de plus de 6 mois si nécessaire.
- Les configurations sont immuables en base (`rule_configs` sans `UPDATE`) : sans cela, le snapshot ne suffirait pas.
