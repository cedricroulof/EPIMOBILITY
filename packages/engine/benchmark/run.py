#!/usr/bin/env python3
"""Banc d'essai du moteur : scénarios × algorithmes, invariants, stabilité, rejeu, montée en charge.

    pnpm bench                                                   # rapport dans docs/technical/benchmark-results.md
    uv run python packages/engine/benchmark/run.py --out /tmp/r.md  # autre destination

Code de sortie 1 si une vérification de justesse échoue.
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
BUDGET_MS = 500  # budget pour tout le calcul d'un run 1 000 × 100 dans la requête HTTP (ADR-0004)


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

    # ── 1. Comparatif par scénario ─────────────────────────────────────────────
    md += [
        "## 1. Comparatif par scénario (1 000 étudiants × 100 universités, seed 42)",
        "",
        "| Scénario | Algorithme | 1er vœu | Non affectés | Rang moyen | Paires bloquantes | Taux de remplissage "
        "| Préparation | Affectation | Détection paires bloquantes |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    summaries = {}
    cfg_ov = copy.deepcopy(
        cfg
    )  # variante : les 15 universités les plus disputées (candidats éligibles / places) pondèrent l'anglais à 60 %
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
        generator.draw_lottery(students, 42)  # comme le fera l'API au snapshot, avec run.seed
        p, t_prep = med(lambda: algorithms.Problem(unis, students, config))
        for algo in ALGOS:
            res, t_match = med(lambda: algorithms.ALGORITHMS[algo](p))
            _, t_stab = med(lambda: metrics.blocking_pairs(res, p))
            summ = metrics.summarize(res, p)
            summaries[(sc, algo)] = summ
            md.append(
                f"| {sc} | {algo} | {summ['pct_first']} % | {summ['pct_unassigned']} % | {summ['mean_rank']} | "
                f"{summ['blocking_pairs']} | {summ['fill_rate']} % | "
                f"{t_prep:.1f} ms | {t_match:.1f} ms | {t_stab:.1f} ms |"
            )
            check(
                f"{sc}/{algo} : invariants (vœux, éligibilité, capacités)",
                not summ["violations"],
                "; ".join(summ["violations"][:3]),
            )
            check(
                f"{sc}/{algo} : explications cohérentes avec les planchers", not metrics.explanation_violations(res, p)
            )
            if algo == "gale_shapley":
                check(
                    f"{sc}/gale_shapley : 0 paire bloquante (stabilité)",
                    summ["blocking_pairs"] == 0,
                    str(summ["blocking_pairs"]),
                )
                check(
                    f"{sc}/gale_shapley : budget {BUDGET_MS} ms (préparation + affectation + vérification)",
                    t_prep + t_match + t_stab < BUDGET_MS,
                    f"{t_prep + t_match + t_stab:.0f} ms",
                )
        gs, bo = summaries[(sc, "gale_shapley")], summaries[(sc, "boston")]
        check(
            f"{sc} : Boston sert au moins autant de 1ers vœux que Gale-Shapley (propriété théorique)",
            bo["pct_first"] >= gs["pct_first"],
            f"boston {bo['pct_first']} vs GS {gs['pct_first']}",
        )
    md += [
        "",
        "Lecture : Boston maximise les premiers vœux mais crée des paires bloquantes (un étudiant et une université "
        "qui se préféreraient mutuellement à leur affectation). "
        "Gale-Shapley n'en crée jamais, au prix de quelques premiers vœux.",
        "",
    ]
    check(
        "Le vérificateur de stabilité détecte bien l'instabilité (Boston > 0 paires sur au moins un scénario)",
        any(summaries[(sc, "boston")]["blocking_pairs"] > 0 for sc in generator.SCENARIOS),
    )
    check(
        "Pondérations par université (overrides) : Gale-Shapley reste stable "
        "et le classement diffère entre universités",
        summaries[("nominal + overrides", "gale_shapley")]["blocking_pairs"] == 0
        and summaries[("nominal + overrides", "gale_shapley")]["pct_first"]
        != summaries[("nominal", "gale_shapley")]["pct_first"],
    )

    md += [
        "### Répartition des rangs obtenus (scénario nominal)",
        "",
        "| Algorithme | " + " | ".join(f"Vœu {r}" for r in range(1, 6)) + " | Non affecté |",
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

    # ── 2. Reproductibilité, rejeu, déterminisme, règles ─────────────────────
    unis, students = generator.generate("nominal")
    generator.draw_lottery(students, 42)
    h1, h2, h3 = (generator.dataset_hash(*generator.generate("nominal", seed=s)) for s in (42, 42, 43))
    check("Générateur : même seed ⇒ jeu de données identique (hash)", h1 == h2, h1)
    check("Générateur : seed différent ⇒ jeu de données différent", h1 != h3, f"{h1} vs {h3}")
    continents = {u.continent for u in unis}
    check(
        "Générateur : les 6 continents habités sont couverts",
        continents == set(generator.CONTINENTS),
        str(sorted(continents)),
    )
    check(
        "Générateur : 5 vœux distincts et valides pour chaque étudiant",
        all(len(set(s.wishes)) == 5 and set(s.wishes) <= {u.id for u in unis} for s in students),
    )
    snap_kb = len(generator.snapshot(unis, students).encode()) / 1024
    check("Snapshot d'entrée d'un run (stocké en JSONB pour le rejeu) < 1 Mo", snap_kb < 1024, f"{snap_kb:.0f} Ko")

    for algo in ALGOS:
        r1, _ = run(unis, students, cfg, algo)
        r2, _ = run(unis, students, cfg, algo)
        check(
            f"Rejeu/{algo} : même snapshot + même config ⇒ affectation identique",
            r1.output_hash() == r2.output_hash(),
            r1.output_hash(),
        )
        rng = random.Random(7)
        su, ss = unis[:], students[:]
        rng.shuffle(su), rng.shuffle(ss)
        r3, _ = run(su, ss, cfg, algo)
        check(
            f"Déterminisme/{algo} : ordre des lignes en entrée mélangé ⇒ même affectation",
            r1.output_hash() == r3.output_hash(),
        )

    cfg2 = copy.deepcopy(cfg)
    cfg2["criteria"][0]["weight"], cfg2["criteria"][1]["weight"] = 0.2, 0.6
    r_a, _ = run(unis, students, cfg, "gale_shapley")
    r_b, _ = run(unis, students, cfg2, "gale_shapley")
    check(
        "Versionnage : modifier un poids ⇒ nouvel identifiant de configuration",
        rules.config_id(cfg) != rules.config_id(cfg2),
        f"{rules.config_id(cfg)} → {rules.config_id(cfg2)}",
    )
    moved = sum(r_a.assignment[s] != r_b.assignment[s] for s in r_a.assignment)
    check(
        "Mode « et si » : la nouvelle pondération change réellement des affectations",
        moved > 0,
        f"{moved} étudiants déplacés",
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
        "Nouveau critère sans code : bonus « projet perso » + malus « absences » ajoutés par config seule, "
        "affectation modifiée, toujours stable",
        moved3 > 0 and not metrics.blocking_pairs(r_c, p_c),
        f"{moved3} étudiants déplacés",
    )

    try:
        rules.validate(
            {
                "criteria": [{"key": "gpaa", "weight": "lourd", "min": 4, "max": 0}],
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
            "Validation : une configuration invalide est rejetée avec toutes ses erreurs "
            "(types, opérateurs, clés inconnues, niveau CEFR)",
            False,
        )
    except ValueError as e:
        check(
            "Validation : une configuration invalide est rejetée avec toutes ses erreurs "
            "(types, opérateurs, clés inconnues, niveau CEFR)",
            str(e).count(";") >= 5,
            f"{str(e).count(';') + 1} erreurs listées",
        )
    cfg4 = copy.deepcopy(cfg)
    cfg4["eliminatory"][1] = {"key": "english_cefr", "op": ">=", "value": "C1"}
    r_d, p_d = run(unis, students, cfg4, "gale_shapley")
    check(
        "Seuil CEFR en constante (« C1 ») : accepté, appliqué, affectation stable",
        not metrics.blocking_pairs(r_d, p_d)
        and sum(1 for s in students if p_d.eligible[s.id]) < sum(1 for s in students if p_c.eligible[s.id]),
    )

    # ── 3. Montée en charge ────────────────────────────────────────────────────
    md += [
        "## 2. Montée en charge (marge au-delà du besoin : 1 000 × 100)",
        "",
        "| Étudiants | Universités | Algorithme | Préparation | Affectation | Détection paires bloquantes | Total |",
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
                    f"| {n_s:,} | {n_u:,} | {algo} | {t_prep:.0f} ms | {t_match:.0f} ms | {t_stab:.0f} ms "
                    f"| {t_prep + t_match + t_stab:.0f} ms |"
                ).replace(",", " ")
            )
            if algo == "gale_shapley":
                check(f"Échelle {n_s}×{n_u} : Gale-Shapley reste stable", not bp)
    md.append("")

    # ── 4. Rapport ────────────────────────────────────────────────────────────
    failed = [c for c in checks if not c[1]]
    md += [f"## 3. Vérifications de justesse : {len(checks) - len(failed)}/{len(checks)} réussies", ""]
    md += [f"- {'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail else "") for name, ok, detail in checks]
    md += [
        "",
        "## Environnement",
        "",
        f"- Python {platform.python_version()}, {platform.machine()}, {platform.system()} {platform.release()}",
        f"- Temps : médiane de {REPEAT} exécutions (1 seule exécution au-delà de 1 000 étudiants), "
        "`time.perf_counter` ; les temps varient d'une machine et d'une exécution à l'autre, "
        "seules les vérifications sont comparables entre deux rapports",
        f"- Généré par `pnpm bench` le {time.strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    report = "\n".join(["# Résultats du banc d'essai du moteur d'affectation", ""] + md)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(report)
    if failed:
        print(f"\n{len(failed)} vérification(s) en échec", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    out = (
        pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
        if "--out" in sys.argv
        else ROOT / "docs" / "technical" / "benchmark-results.md"
    )
    sys.exit(main(out))
