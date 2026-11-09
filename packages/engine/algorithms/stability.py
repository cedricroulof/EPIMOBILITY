"""Automatic stability and invariant checks. Reads ONLY the final assignment and the `Problem`:
independent of the algorithms, hence able to judge them (a checker sharing their code would share their bugs)."""

from collections import defaultdict


def violations(result, p):
    """Invariants that every algorithm must respect. Empty list = OK."""
    out = []
    filled = defaultdict(int)
    for s in p.students:
        u = result.assignment[s.id]
        if u is None:
            continue
        filled[u] += 1
        if u not in s.wishes:
            out.append(f"{s.id} assigned outside their wishes ({u})")
        if s.id not in p.rank[u]:
            out.append(f"{s.id} assigned to {u} although ineligible there")
    for u, n in filled.items():
        if n > p.cap[u]:
            out.append(f"{u} over capacity: {n}/{p.cap[u]}")
    return out


def blocking_pairs(result, p):
    """(s, u) is blocking ⇔ s prefers u to their assignment AND (u has a free seat OR u prefers s to its worst
    admitted student). O(Σ wishes). Zero pairs ⇔ stable assignment."""
    held = defaultdict(list)
    for s, u in result.assignment.items():
        if u is not None:
            held[u].append(s)
    worst = {u: max(p.rank[u][s] for s in lst) for u, lst in held.items()}
    pairs = []
    for s in p.students:
        a = result.assignment[s.id]
        for u in s.wishes:
            if u == a:
                break  # later wishes are less desired: not blocking
            if s.id not in p.rank[u]:
                continue  # ineligible: u does not want s
            if len(held[u]) < p.cap[u] or p.rank[u][s.id] < worst.get(u, -1):
                pairs.append((s.id, u))
    return pairs
