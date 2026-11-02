"""Comparatif chiffré (% de 1ers vœux, % de non-affectés, rang moyen, stabilité) et explications par étudiant."""

import statistics

from .stability import blocking_pairs, violations


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
