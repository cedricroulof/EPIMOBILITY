"""Comparatif chiffré, vérification automatique de stabilité, invariants et explications par étudiant.

Tout ici ne lit QUE l'affectation finale et le `Problem` : indépendant des algorithmes, donc apte à
les juger (un vérificateur qui partagerait leur code partagerait leurs bugs).
"""

import statistics
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


def summarize(result, p):
    n = len(p.students)
    ranks = [s.wishes.index(result.assignment[s.id]) + 1 for s in p.students if result.assignment[s.id] is not None]
    max_rank = max((len(s.wishes) for s in p.students), default=0)
    hist = {r: ranks.count(r) for r in range(1, max_rank + 1)}
    return {
        "algorithm": result.algorithm,
        "students": n,
        "assigned": len(ranks),
        "pct_first": round(100 * hist.get(1, 0) / n, 1),
        "pct_unassigned": round(100 * (n - len(ranks)) / n, 1),
        "mean_rank": round(statistics.fmean(ranks), 3) if ranks else None,
        "rank_hist": hist,
        "blocking_pairs": len(blocking_pairs(result, p)),
        "fill_rate": round(100 * len(ranks) / sum(p.cap.values()), 1) if sum(p.cap.values()) else None,
        "violations": violations(result, p),
    }


def explain(student, result, p):
    """Pour chaque vœu : pourquoi obtenu / refusé / inéligible / non examiné. Répond à « pourquoi ce vœu et pas le précédent ? »."""
    a = result.assignment[student.id]
    a_rank = student.wishes.index(a) if a is not None else None
    out = []
    for i, u in enumerate(student.wishes):
        e = {"rank": i + 1, "university": u, "score": p.score[(student.id, u)]}
        if u == a:
            e["status"], e["cutoff"] = "assigned", result.round_cutoff.get((u, i), result.cutoff.get(u))
        elif a_rank is not None and i > a_rank:
            e["status"] = "not_considered"
        elif p.reasons[(student.id, u)]:
            e["status"], e["failed"] = "ineligible", p.reasons[(student.id, u)]
        else:  # éligible mais refusé : complet, et le dernier admis avait un meilleur rang
            e["status"], e["cutoff"] = "rejected", result.round_cutoff.get((u, i), result.cutoff.get(u))
        out.append(e)
    return out


def explanation_violations(result, p):
    """Cohérence des explications : un refusé n'excède pas le plancher annoncé, un admis l'atteint ; un vœu refusé
    sans plancher (`cutoff: null`) n'est possible que si l'université n'avait aucune place ouverte à ce moment."""
    out = []
    for s in p.students:
        for e in explain(s, result, p):
            if e["status"] == "rejected" and e["cutoff"] is not None and e["score"] > e["cutoff"]:
                out.append(f"{s.id} refusé à {e['university']} : score {e['score']} > plancher {e['cutoff']}")
            if e["status"] == "assigned" and e["cutoff"] is not None and e["score"] < e["cutoff"]:
                out.append(f"{s.id} admis à {e['university']} : score {e['score']} < plancher {e['cutoff']}")
            if (
                e["status"] == "rejected"
                and e["cutoff"] is None
                and p.cap[e["university"]] > 0
                and result.algorithm == "gale_shapley"
            ):
                out.append(f"{s.id} refusé à {e['university']} sans plancher alors que des places existaient")
    return out
