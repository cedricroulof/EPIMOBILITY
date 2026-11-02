"""Vérification automatique de stabilité et invariants. Ne lit QUE l'affectation finale et le `Problem` :
indépendante des algorithmes, donc apte à les juger (un vérificateur qui partagerait leur code partagerait leurs bugs)."""

from collections import defaultdict


def violations(result, p):
    """Invariants que tout algorithme doit respecter. Liste vide = OK."""
    out = []
    filled = defaultdict(int)
    for s in p.students:
        u = result.assignment[s.id]
        if u is None:
            continue
        filled[u] += 1
        if u not in s.wishes:
            out.append(f"{s.id} affecté hors de ses vœux ({u})")
        if s.id not in p.rank[u]:
            out.append(f"{s.id} affecté à {u} alors qu'il y est inéligible")
    for u, n in filled.items():
        if n > p.cap[u]:
            out.append(f"{u} en sur-capacité : {n}/{p.cap[u]}")
    return out


def blocking_pairs(result, p):
    """(s, u) bloquante ⇔ s préfère u à son affectation ET (u a une place libre OU u préfère s à son pire admis).
    O(Σ vœux). Zéro paire ⇔ affectation stable."""
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
                break  # les vœux suivants sont moins désirés : pas bloquants
            if s.id not in p.rank[u]:
                continue  # inéligible : u ne veut pas de s
            if len(held[u]) < p.cap[u] or p.rank[u][s.id] < worst.get(u, -1):
                pairs.append((s.id, u))
    return pairs
