"""Moteur d'affectation : module pur (aucune I/O, aucune dépendance) — testable et benchable sans base de données.

generator  → universités et étudiants fictifs, reproductibles (seed), scénarios de tension
rules      → configuration JSON interprétée : pondérations, seuils éliminatoires, bonus, départage
matching   → Gale-Shapley (acceptation différée, capacités) et Boston (acceptation immédiate)
metrics    → comparatif chiffré, vérification automatique de stabilité, invariants, explications
english    → échelle d'anglais commune (bandes CEFR), sourcée

ENGINE_VERSION est stocké dans chaque run : un rejeu `identical: false` après mise à jour du moteur s'explique par ce champ.
"""

ENGINE_VERSION = "1.0.0"
