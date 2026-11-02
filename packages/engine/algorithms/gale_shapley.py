"""Gale-Shapley : acceptation différée, étudiants proposants, avec capacités (hospitals/residents).
Stable (aucune paire bloquante), optimal pour les étudiants, non manipulable par eux."""

import heapq
from collections import deque

from .problem import Problem, Result


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
