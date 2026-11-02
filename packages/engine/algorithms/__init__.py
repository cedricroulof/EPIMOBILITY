"""Algorithmes d'affectation, tous sur la même instance pré-calculée (`Problem`).

gale_shapley.py : algorithme de publication, stable
boston.py       : point de comparaison, instable (ADR-0006)
stability.py    : vérification automatique de stabilité et invariants, indépendante des algorithmes
metrics.py      : comparatif chiffré et explication par étudiant
"""

from .boston import boston
from .gale_shapley import gale_shapley
from .problem import Problem, Result

ALGORITHMS = {"gale_shapley": gale_shapley, "boston": boston}
__all__ = ["ALGORITHMS", "Problem", "Result", "boston", "gale_shapley"]
