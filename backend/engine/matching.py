"""Deux algorithmes d'affectation sur la même instance pré-calculée (`Problem`).

gale_shapley : acceptation différée, étudiants proposants, avec capacités (hospitals/residents).
               Stable (aucune paire bloquante), optimal pour les étudiants, non manipulable par eux.
boston       : acceptation immédiate, vœu par vœu. Maximise le nombre de 1ers vœux servis,
               mais instable et manipulable. Sert de point de comparaison « intuitif ».
"""

import hashlib
import heapq
import json
from collections import defaultdict, deque
from dataclasses import dataclass, field

from . import rules


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


def gale_shapley(p: Problem) -> Result:
    held = {u: [] for u in p.cap}  # tas de (-rang, s) : le sommet est le pire admis provisoire
    nxt = {s.id: 0 for s in p.students}
    free = deque(s.id for s in p.students)
    while free:
        s = free.popleft()
        wl = p.eligible[s]
        while nxt[s] < len(wl):
            u = wl[nxt[s]]
            nxt[s] += 1
            if p.cap[u] <= 0:
                continue
            r = p.rank[u][s]
            if len(held[u]) < p.cap[u]:
                heapq.heappush(held[u], (-r, s))
                break
            worst_r, worst = held[u][0]
            if r < -worst_r:  # u préfère s à son pire admis : s remplace, l'évincé redevient libre
                heapq.heapreplace(held[u], (-r, s))
                free.append(worst)
                break
    assignment = {s.id: None for s in p.students}
    cutoff = {}
    for u, h in held.items():
        for _, s in h:
            assignment[s] = u
        if h:
            cutoff[u] = p.score[(h[0][1], u)]
    return Result("gale_shapley", assignment, cutoff)


def boston(p: Problem) -> Result:
    assignment = {s.id: None for s in p.students}
    filled = defaultdict(int)
    cutoff, round_cutoff = {}, {}
    for rnd in range(max((len(s.wishes) for s in p.students), default=0)):
        apps = defaultdict(list)
        for s in p.students:
            if assignment[s.id] is None and rnd < len(s.wishes) and s.id in p.rank[s.wishes[rnd]]:
                apps[s.wishes[rnd]].append(s.id)
        for u, lst in apps.items():
            lst.sort(key=p.rank[u].__getitem__)
            seats = p.cap[u] - filled[u]
            for s in lst[:seats]:
                assignment[s] = u
            filled[u] += min(seats, len(lst))
            if seats > 0:  # plancher de ce tour = dernier admis du tour ; plancher final = plus bas admis tous tours
                last = p.score[(lst[min(seats, len(lst)) - 1], u)]
                round_cutoff[(u, rnd)] = last
                cutoff[u] = min(cutoff.get(u, last), last)
            else:
                round_cutoff[(u, rnd)] = None  # déjà complet avant ce tour
    return Result("boston", assignment, cutoff, round_cutoff)


ALGORITHMS = {"gale_shapley": gale_shapley, "boston": boston}
