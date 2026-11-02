"""Moteur d'affectation : module pur (aucune I/O, aucune dépendance) — testable et benchable sans base de données.

rules/       → configuration JSON interprétée : pondérations, seuils éliminatoires, bonus, départage ;
               english.py : échelle d'anglais commune (bandes CEFR), sourcée
algorithms/  → Gale-Shapley et Boston sur un prétraitement commun, vérification de stabilité, comparatif, explications
benchmark/   → banc d'essai : temps par algorithme de 1 000 à 50 000 étudiants, 68 vérifications
Les données d'entrée (universités, étudiants fictifs, seed) viennent de `packages/generator`.

ENGINE_VERSION est stocké dans chaque run : un rejeu `identical: false` après mise à jour du moteur s'explique par ce champ.
"""

ENGINE_VERSION = "1.0.0"
