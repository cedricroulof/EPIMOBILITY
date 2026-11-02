"""Prétraitement commun aux algorithmes (`Problem`) et forme de leur résultat (`Result`) : comparaison à conditions égales."""

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field

from .. import rules


class Problem:
    """Pré-calcul partagé : score de chaque (étudiant, vœu), éligibilité, et rang de chaque candidat dans chaque université.
    Valide la configuration CONTRE les données (clés réellement présentes) et les entrées (vœux distincts, universités connues)."""

    def __init__(self, universities, students, config):
        s_keys = {k for s in students for k in s.attributes}
        u_keys = {k for u in universities for k in u.attributes}
        rules.validate(config, student_keys=s_keys, university_keys=u_keys)
        self.students = students
        self.unis = {u.id: u for u in universities}
        self.cap = {u.id: u.capacity for u in universities}
        errors = [f"{u.id} : capacité négative" for u in universities if u.capacity < 0]
        errors += [f"{s.id} : vœux en double" for s in students if len(set(s.wishes)) != len(s.wishes)]
        errors += [f"{s.id} : université inconnue {w!r}" for s in students for w in s.wishes if w not in self.unis]
        if errors:
            raise ValueError("entrées invalides : " + " ; ".join(errors[:10]))
        self.score = {}  # (s, u) -> score de s pour u (peut dépendre de u via `overrides`)
        self.reasons = {}  # (s, u) -> seuils échoués (vide = éligible)
        self.rank = {u: {} for u in self.unis}  # u -> {s: position dans la préférence de u} (éligibles seulement)
        self.eligible = {}  # s -> ses vœux éligibles, dans son ordre
        applicants = defaultdict(list)
        overrides = config.get("overrides", {})
        for s in students:
            self.eligible[s.id] = []
            base = rules.score(
                s, config
            )  # une fois par étudiant ; recalculé seulement pour les universités avec override
            for u in s.wishes:
                uni = self.unis[u]
                self.score[(s.id, u)] = rules.score(s, config, uni) if u in overrides else base
                failed = rules.failed_thresholds(s, uni, config)
                self.reasons[(s.id, u)] = failed
                if not failed:
                    applicants[u].append(s)
                    self.eligible[s.id].append(u)
        for u, apps in applicants.items():
            uni = self.unis[u]
            apps.sort(key=lambda s: rules.rank_key(s, config, uni, self.score[(s.id, u)]))
            self.rank[u] = {s.id: i for i, s in enumerate(apps)}


@dataclass
class Result:
    algorithm: str
    assignment: dict  # étudiant -> université | None
    cutoff: dict = field(default_factory=dict)  # u -> plancher final : plus bas score admis
    round_cutoff: dict = field(
        default_factory=dict
    )  # boston : (u, tour) -> dernier admis à ce tour (None = déjà complet)

    def output_hash(self) -> str:
        return hashlib.sha256(json.dumps(sorted(self.assignment.items())).encode()).hexdigest()[:16]
