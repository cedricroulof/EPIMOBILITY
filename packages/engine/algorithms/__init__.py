"""Matching algorithms, all running on the same precomputed instance (`Problem`).

gale_shapley.py: publication algorithm, stable
boston.py:       comparison point, unstable (ADR-0006)
stability.py:    automatic stability and invariant checks, independent of the algorithms
metrics.py:      numeric comparison and per-student explanation
"""

from .boston import boston
from .gale_shapley import gale_shapley
from .problem import Problem, Result

ALGORITHMS = {"gale_shapley": gale_shapley, "boston": boston}
__all__ = ["ALGORITHMS", "Problem", "Result", "boston", "gale_shapley"]
