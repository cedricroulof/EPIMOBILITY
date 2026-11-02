"""Boston : acceptation immédiate, vœu par vœu. Maximise le nombre de 1ers vœux servis, mais instable et manipulable.
Point de comparaison « intuitif » (ADR-0006) ; non publiable."""

from collections import defaultdict

from .problem import Problem, Result


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
