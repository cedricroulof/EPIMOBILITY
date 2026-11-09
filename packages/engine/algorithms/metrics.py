"""Numeric comparison (% of 1st wishes, % unassigned, average rank, stability) and per-student explanations."""

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
    """For each wish: why it was obtained / rejected / ineligible / not considered.
    Answers "why this wish and not the previous one?"."""
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
        else:  # eligible but rejected: full, and the last admitted student had a better rank
            e["status"], e["cutoff"] = "rejected", result.round_cutoff.get((u, i), result.cutoff.get(u))
        out.append(e)
    return out


def explanation_violations(result, p):
    """Consistency of explanations: a rejected student does not exceed the stated cutoff, an admitted student reaches
    it; a rejected wish with no cutoff (`cutoff: null`) is only possible if the university had no open seat at that
    moment."""
    out = []
    for s in p.students:
        for e in explain(s, result, p):
            if e["status"] == "rejected" and e["cutoff"] is not None and e["score"] > e["cutoff"]:
                out.append(f"{s.id} rejected by {e['university']}: score {e['score']} > cutoff {e['cutoff']}")
            if e["status"] == "assigned" and e["cutoff"] is not None and e["score"] < e["cutoff"]:
                out.append(f"{s.id} admitted to {e['university']}: score {e['score']} < cutoff {e['cutoff']}")
            if (
                e["status"] == "rejected"
                and e["cutoff"] is None
                and p.cap[e["university"]] > 0
                and result.algorithm == "gale_shapley"
            ):
                out.append(f"{s.id} rejected by {e['university']} with no cutoff although seats existed")
    return out
