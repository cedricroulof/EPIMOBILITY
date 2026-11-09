#!/usr/bin/env python3
"""Engine benchmark: scenarios × algorithms, invariants, stability, replay, scaling.

    pnpm bench                                                   # report written to docs/technical/benchmark-results.md
    uv run python packages/engine/benchmark/run.py --out /tmp/r.md  # other destination

Exit code 1 if a correctness check fails.
"""

import copy
import pathlib
import platform
import random
import statistics
import sys
import time

import generator
from engine import algorithms, rules
from engine.algorithms import metrics

ROOT = pathlib.Path(__file__).resolve().parents[3]

ALGOS = list(algorithms.ALGORITHMS)
REPEAT = 5
BUDGET_MS = 500  # budget for the whole computation of a 1,000 × 100 run inside the HTTP request (ADR-0004)


def med(fn, repeat=REPEAT):
    ts = []
    for _ in range(repeat):
        t = time.perf_counter()
        out = fn()
        ts.append((time.perf_counter() - t) * 1000)
    return out, statistics.median(ts)


def run(unis, students, config, algo):
    p = algorithms.Problem(unis, students, config)
    return algorithms.ALGORITHMS[algo](p), p


def main(out_path):
    cfg = rules.DEFAULT_CONFIG
    checks, md = [], []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    # ── 1. Comparison by scenario ──────────────────────────────────────────────
    md += [
        "## 1. Comparison by scenario (1,000 students × 100 universities, seed 42)",
        "",
        "| Scenario | Algorithm | 1st wish | Unassigned | Average rank | Blocking pairs | Fill rate | Preparation "
        "| Assignment | Blocking pair detection |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    summaries = {}
    cfg_ov = copy.deepcopy(
        cfg
    )  # variant: the 15 most contested universities (eligible applicants / seats) weight English at 60%
    unis0, st0 = generator.generate("nominal")
    generator.draw_lottery(st0, 42)
    p0 = algorithms.Problem(unis0, st0, cfg)
    for u in sorted(unis0, key=lambda u: -len(p0.rank[u.id]) / max(1, u.capacity))[:15]:
        cfg_ov["overrides"][u.id] = {
            "criteria": [
                {"key": "gpa", "weight": 0.3, "min": 0, "max": 4},
                {"key": "english_pct", "weight": 0.6, "min": 0, "max": 100},
                {"key": "associative", "weight": 0.1, "min": 0, "max": 100},
            ]
        }
    cases = [(sc, sc, cfg) for sc in generator.SCENARIOS] + [("nominal + overrides", "nominal", cfg_ov)]
    for sc, data_sc, config in cases:
        unis, students = generator.generate(data_sc)
        generator.draw_lottery(students, 42)  # as the API will do at snapshot time, with run.seed
        p, t_prep = med(lambda: algorithms.Problem(unis, students, config))
        for algo in ALGOS:
            res, t_match = med(lambda: algorithms.ALGORITHMS[algo](p))
            _, t_stab = med(lambda: metrics.blocking_pairs(res, p))
            summ = metrics.summarize(res, p)
            summaries[(sc, algo)] = summ
            md.append(
                f"| {sc} | {algo} | {summ['pct_first']} % | {summ['pct_unassigned']} % | {summ['mean_rank']} | "
                f"{summ['blocking_pairs']} | {summ['fill_rate']} % | {t_prep:.1f} ms | {t_match:.1f} ms | "
                f"{t_stab:.1f} ms |"
            )
            check(
                f"{sc}/{algo}: invariants (wishes, eligibility, capacities)",
                not summ["violations"],
                "; ".join(summ["violations"][:3]),
            )
            check(f"{sc}/{algo}: explanations consistent with the cutoffs", not metrics.explanation_violations(res, p))
            if algo == "gale_shapley":
                check(
                    f"{sc}/gale_shapley: 0 blocking pairs (stability)",
                    summ["blocking_pairs"] == 0,
                    str(summ["blocking_pairs"]),
                )
                check(
                    f"{sc}/gale_shapley: budget {BUDGET_MS} ms (preparation + assignment + check)",
                    t_prep + t_match + t_stab < BUDGET_MS,
                    f"{t_prep + t_match + t_stab:.0f} ms",
                )
        gs, bo = summaries[(sc, "gale_shapley")], summaries[(sc, "boston")]
        check(
            f"{sc}: Boston serves at least as many 1st wishes as Gale-Shapley (theoretical property)",
            bo["pct_first"] >= gs["pct_first"],
            f"boston {bo['pct_first']} vs GS {gs['pct_first']}",
        )
    md += [
        "",
        "How to read this: Boston maximizes first wishes but creates blocking pairs (a student and a university "
        "that would prefer each other to their assignment). Gale-Shapley never creates any, at the cost of a few "
        "first wishes.",
        "",
    ]
    check(
        "The stability checker does detect instability (Boston > 0 pairs on at least one scenario)",
        any(summaries[(sc, "boston")]["blocking_pairs"] > 0 for sc in generator.SCENARIOS),
    )
    check(
        "Per-university weights (overrides): Gale-Shapley stays stable and the ranking differs between universities",
        summaries[("nominal + overrides", "gale_shapley")]["blocking_pairs"] == 0
        and summaries[("nominal + overrides", "gale_shapley")]["pct_first"]
        != summaries[("nominal", "gale_shapley")]["pct_first"],
    )

    md += [
        "### Distribution of obtained ranks (nominal scenario)",
        "",
        "| Algorithm | " + " | ".join(f"Wish {r}" for r in range(1, 6)) + " | Unassigned |",
        "|---|" + "---:|" * 6,
    ]
    for algo in ALGOS:
        s = summaries[("nominal", algo)]
        md.append(
            f"| {algo} | "
            + " | ".join(str(s["rank_hist"].get(r, 0)) for r in range(1, 6))
            + f" | {s['students'] - s['assigned']} |"
        )
    md.append("")

    # ── 2. Reproducibility, replay, determinism, rules ───────────────────────
    unis, students = generator.generate("nominal")
    generator.draw_lottery(students, 42)
    h1, h2, h3 = (generator.dataset_hash(*generator.generate("nominal", seed=s)) for s in (42, 42, 43))
    check("Generator: same seed ⇒ identical dataset (hash)", h1 == h2, h1)
    check("Generator: different seed ⇒ different dataset", h1 != h3, f"{h1} vs {h3}")
    continents = {u.continent for u in unis}
    check(
        "Generator: the 6 inhabited continents are covered",
        continents == set(generator.CONTINENTS),
        str(sorted(continents)),
    )
    check(
        "Generator: 5 distinct and valid wishes for each student",
        all(len(set(s.wishes)) == 5 and set(s.wishes) <= {u.id for u in unis} for s in students),
    )
    snap_kb = len(generator.snapshot(unis, students).encode()) / 1024
    check("Input snapshot of a run (stored as JSONB for replay) < 1 MB", snap_kb < 1024, f"{snap_kb:.0f} KB")

    for algo in ALGOS:
        r1, _ = run(unis, students, cfg, algo)
        r2, _ = run(unis, students, cfg, algo)
        check(
            f"Replay/{algo}: same snapshot + same config ⇒ identical assignment",
            r1.output_hash() == r2.output_hash(),
            r1.output_hash(),
        )
        rng = random.Random(7)
        su, ss = unis[:], students[:]
        rng.shuffle(su), rng.shuffle(ss)
        r3, _ = run(su, ss, cfg, algo)
        check(
            f"Determinism/{algo}: shuffled input row order ⇒ same assignment",
            r1.output_hash() == r3.output_hash(),
        )

    cfg2 = copy.deepcopy(cfg)
    cfg2["criteria"][0]["weight"], cfg2["criteria"][1]["weight"] = 0.2, 0.6
    r_a, _ = run(unis, students, cfg, "gale_shapley")
    r_b, _ = run(unis, students, cfg2, "gale_shapley")
    check(
        "Versioning: changing a weight ⇒ new configuration id",
        rules.config_id(cfg) != rules.config_id(cfg2),
        f"{rules.config_id(cfg)} → {rules.config_id(cfg2)}",
    )
    moved = sum(r_a.assignment[s] != r_b.assignment[s] for s in r_a.assignment)
    check(
        "What-if mode: the new weights really change assignments",
        moved > 0,
        f"{moved} students moved",
    )

    cfg3 = copy.deepcopy(cfg)
    cfg3["bonuses"].append({"key": "personal_project", "op": "==", "value": True, "points": 15})
    cfg3["criteria"].append({"key": "absences", "weight": -0.1, "min": 0, "max": 20, "default": 0})
    st3 = copy.deepcopy(students)
    rng = random.Random(1)
    for s in st3:
        if rng.random() < 0.1:
            s.attributes["personal_project"] = True
        s.attributes["absences"] = rng.choice([0, 0, 0, 2, 5, 12])
    r_c, p_c = run(unis, st3, cfg3, "gale_shapley")
    moved3 = sum(r_a.assignment[s] != r_c.assignment[s] for s in r_a.assignment)
    check(
        'New criterion without code: "personal project" bonus + "absences" penalty added by config alone, '
        "assignment changed, still stable",
        moved3 > 0 and not metrics.blocking_pairs(r_c, p_c),
        f"{moved3} students moved",
    )

    try:
        rules.validate(
            {
                "criteria": [{"key": "gpaa", "weight": "heavy", "min": 4, "max": 0}],
                "eliminatory": [
                    {"key": "gpa", "op": "~"},
                    {"key": "english_cefr", "op": ">=", "value": "Z9"},
                    {"key": "gpa", "op": ">=", "ref": "min_x"},
                ],
            },
            student_keys=set(),
            university_keys=set(),
        )
        check(
            "Validation: an invalid configuration is rejected with all its errors "
            "(types, operators, unknown keys, CEFR level)",
            False,
        )
    except ValueError as e:
        check(
            "Validation: an invalid configuration is rejected with all its errors "
            "(types, operators, unknown keys, CEFR level)",
            str(e).count(";") >= 5,
            f"{str(e).count(';') + 1} errors listed",
        )
    cfg4 = copy.deepcopy(cfg)
    cfg4["eliminatory"][1] = {"key": "english_cefr", "op": ">=", "value": "C1"}
    r_d, p_d = run(unis, students, cfg4, "gale_shapley")
    check(
        'CEFR threshold as a constant ("C1"): accepted, applied, stable assignment',
        not metrics.blocking_pairs(r_d, p_d)
        and sum(1 for s in students if p_d.eligible[s.id]) < sum(1 for s in students if p_c.eligible[s.id]),
    )

    # ── 3. Scaling ─────────────────────────────────────────────────────────────
    md += [
        "## 2. Scaling (margin beyond the requirement: 1,000 × 100)",
        "",
        "| Students | Universities | Algorithm | Preparation | Assignment | Blocking pair detection | Total |",
        "|---:|---:|---|---:|---:|---:|---:|",
    ]
    for n_s, n_u in ((1_000, 100), (10_000, 1_000), (50_000, 1_000)):
        unis_l, st_l = generator.generate("nominal", n_students=n_s, n_unis=n_u)
        generator.draw_lottery(st_l, 42)
        p, t_prep = med(lambda: algorithms.Problem(unis_l, st_l, cfg), repeat=1 if n_s > 1000 else REPEAT)
        for algo in ALGOS:
            res, t_match = med(lambda: algorithms.ALGORITHMS[algo](p), repeat=1 if n_s > 1000 else REPEAT)
            bp, t_stab = med(lambda: metrics.blocking_pairs(res, p), repeat=1)
            md.append(
                (
                    f"| {n_s:,} | {n_u:,} | {algo} | {t_prep:.0f} ms | {t_match:.0f} ms | {t_stab:.0f} ms | "
                    f"{t_prep + t_match + t_stab:.0f} ms |"
                ).replace(",", " ")
            )
            if algo == "gale_shapley":
                check(f"Scale {n_s}×{n_u}: Gale-Shapley stays stable", not bp)
    md.append("")

    # ── 4. Report ─────────────────────────────────────────────────────────────
    failed = [c for c in checks if not c[1]]
    md += [f"## 3. Correctness checks: {len(checks) - len(failed)}/{len(checks)} passed", ""]
    md += [f"- {'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail else "") for name, ok, detail in checks]
    md += [
        "",
        "## Environment",
        "",
        f"- Python {platform.python_version()}, {platform.machine()}, {platform.system()} {platform.release()}",
        f"- Times: median of {REPEAT} executions (only 1 execution above 1,000 students), `time.perf_counter`; "
        "times vary from one machine and one execution to another, only the checks are comparable between two reports",
        f"- Generated by `pnpm bench` on {time.strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    report = "\n".join(["# Matching engine benchmark results", ""] + md)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(report)
    if failed:
        print(f"\n{len(failed)} check(s) failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    out = (
        pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
        if "--out" in sys.argv
        else ROOT / "docs" / "technical" / "benchmark-results.md"
    )
    sys.exit(main(out))
