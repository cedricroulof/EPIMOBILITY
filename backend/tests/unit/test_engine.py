"""Tests du moteur : règles, algorithmes (stabilité vérifiée automatiquement), reproductibilité du générateur.

python3 tests/unit/test_engine.py   # sans dépendance
pytest                           # si installé, même fichier
"""

import copy
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from engine import english, generator, matching, metrics, rules  # noqa: E402

CFG = rules.DEFAULT_CONFIG


def solve(unis, students, cfg=CFG, algo="gale_shapley"):
    p = matching.Problem(unis, students, cfg)
    return matching.ALGORITHMS[algo](p), p


def mk(id, gpa=3.0, toeic=800, assoc=50, wishes=("U0",), **attrs):
    return generator.Student(id, gpa, "TOEIC", float(toeic), assoc, list(wishes), dict(attrs))


def uni(id, cap=1, min_gpa=0.0, min_cefr="A1"):
    return generator.University(id, id, "Europe", cap, min_gpa, min_cefr, 0.5)


# ── générateur ────────────────────────────────────────────────────────────────
def test_generator_reproducible():
    a = generator.dataset_hash(*generator.generate("nominal", seed=42))
    b = generator.dataset_hash(*generator.generate("nominal", seed=42))
    c = generator.dataset_hash(*generator.generate("nominal", seed=43))
    assert a == b and a != c


def test_generator_sane():
    unis, students = generator.generate("nominal")
    assert len(unis) == 100 and len(students) == 1000
    assert {u.continent for u in unis} == set(generator.CONTINENTS)
    ids = {u.id for u in unis}
    for s in students:
        assert 1.0 <= s.gpa <= 4.0 and 0 <= s.associative <= 100
        assert len(s.wishes) == 5 == len(set(s.wishes)) and set(s.wishes) <= ids
        assert s.english_cefr in generator.CEFR and 0 <= s.english_pct <= 100
    assert all(u.capacity >= 1 for u in unis)


def test_all_scenarios_generate():
    for sc in generator.SCENARIOS:
        unis, students = generator.generate(sc, n_students=50, n_unis=10)
        assert len(students) == 50


# ── moteur de règles ──────────────────────────────────────────────────────────
def test_validate_rejects_bad_config():
    try:
        rules.validate(
            {
                "criteria": [{"key": "gpa", "weight": "x", "min": 1, "max": 0}],
                "eliminatory": [{"key": "gpa", "op": "~", "ref": "a", "value": 1}],
            }
        )
    except ValueError as e:
        assert "weight" in str(e) and "min" in str(e) and "op inconnu" in str(e) and "exactement un" in str(e)
    else:
        raise AssertionError("config invalide acceptée")
    cfg = copy.deepcopy(CFG)
    cfg["criteria"][0]["key"] = "gpaa"  # faute de frappe
    cfg["eliminatory"][1] = {"key": "english_cefr", "op": ">=", "value": "Z9"}
    cfg["eliminatory"].append({"key": "gpa", "op": ">=", "ref": "min_associative"})
    try:
        rules.validate(cfg, student_keys=set(), university_keys=set())
    except ValueError as e:
        assert "'gpaa' inconnue" in str(e) and "Z9" in str(e) and "'min_associative' inconnu" in str(e)
    else:
        raise AssertionError("clés inconnues acceptées")
    try:  # la même erreur est attrapée au run, contre les données réelles
        matching.Problem([uni("U0")], [mk("S1")], cfg)
    except ValueError:
        pass
    else:
        raise AssertionError("Problem a accepté des clés inconnues")


def test_eliminatory_threshold_blocks_and_explains():
    u = uni("U0", min_gpa=3.5, min_cefr="C1")
    s = mk("S1", gpa=3.0, toeic=800)
    failed = rules.failed_thresholds(s, u, CFG)
    assert [f["key"] for f in failed] == ["gpa", "english_cefr"]
    assert failed[1]["value"] == "B2" and failed[1]["threshold"] == "C1"
    res, p = solve([u], [s])
    assert res.assignment["S1"] is None
    assert metrics.explain(s, res, p)[0]["status"] == "ineligible"


def test_score_weights_and_bonus():
    s = mk("S1", gpa=4.0, toeic=990, assoc=100)
    assert rules.score(s, CFG) == 100.0
    cfg = copy.deepcopy(CFG)
    cfg["bonuses"].append({"key": "personal_project", "op": "==", "value": True, "points": 7})
    assert rules.score(s, cfg) == 100.0  # attribut absent ⇒ pas de bonus
    s.attributes["personal_project"] = True
    assert rules.score(s, cfg) == 107.0


def test_new_criterion_without_code_changes_outcome():
    """Un critère « absences » (malus) ajouté par configuration seule inverse une affectation."""
    u = uni("U0", cap=1)
    strong, weak = mk("S1", gpa=3.8, wishes=("U0",), absences=15), mk("S2", gpa=3.6, wishes=("U0",), absences=0)
    res, _ = solve([u], [strong, weak])
    assert res.assignment["S1"] == "U0"
    cfg = copy.deepcopy(CFG)
    cfg["criteria"].append({"key": "absences", "weight": -0.5, "min": 0, "max": 20, "default": 0})
    res, _ = solve([u], [strong, weak], cfg)
    assert res.assignment["S2"] == "U0" and res.assignment["S1"] is None


def test_tie_break_is_total_and_configurable():
    u = uni("U0", cap=1)
    a, b = mk("S1", gpa=3.0, toeic=700, assoc=50), mk("S2", gpa=3.0, toeic=700, assoc=50)
    res, _ = solve([u], [b, a])
    assert res.assignment["S1"] == "U0"  # dernier départage : id croissant, quel que soit l'ordre d'entrée
    cfg = copy.deepcopy(CFG)
    cfg["tie_break"] = [{"key": "associative", "order": "desc"}]
    b.associative = 60  # score identique après arrondi ? non : associatif pèse 0.2 ⇒ on neutralise le poids
    cfg["criteria"] = [{"key": "gpa", "weight": 1, "min": 0, "max": 4}]
    res, _ = solve([u], [a, b], cfg)
    assert res.assignment["S2"] == "U0"


def test_config_id_tracks_content():
    cfg = copy.deepcopy(CFG)
    assert rules.config_id(cfg) == rules.config_id(CFG)
    cfg["criteria"][0]["weight"] += 0.01
    assert rules.config_id(cfg) != rules.config_id(CFG)


# ── algorithmes ───────────────────────────────────────────────────────────────
def test_gale_shapley_stable_on_all_scenarios():
    for sc in generator.SCENARIOS:
        unis, students = generator.generate(sc, n_students=300, n_unis=40)
        res, p = solve(unis, students)
        assert metrics.violations(res, p) == [], sc
        assert metrics.blocking_pairs(res, p) == [], sc
        assert metrics.explanation_violations(res, p) == [], sc


def test_boston_respects_invariants_but_is_unstable():
    unis, students = generator.generate("tight_capacity")  # pleine échelle : la tension révèle l'instabilité
    res, p = solve(unis, students, algo="boston")
    assert metrics.violations(res, p) == []
    assert metrics.explanation_violations(res, p) == []
    assert len(metrics.blocking_pairs(res, p)) > 0  # le vérificateur voit bien l'instabilité
    gs, _ = solve(unis, students)
    assert metrics.summarize(res, p)["pct_first"] >= metrics.summarize(gs, p)["pct_first"]


def test_blocking_pair_detector_on_handmade_instance():
    """Instance minimale : S1 préfère U1 à U0 et U1 préfère S1 à S2 ⇒ (S1, U1) bloque si on les sépare."""
    u0, u1 = uni("U0"), uni("U1")
    s1, s2 = mk("S1", gpa=3.9, wishes=("U1", "U0")), mk("S2", gpa=3.0, wishes=("U1", "U0"))
    p = matching.Problem([u0, u1], [s1, s2], CFG)
    bad = matching.Result("handmade", {"S1": "U0", "S2": "U1"})
    assert metrics.blocking_pairs(bad, p) == [("S1", "U1")]
    good = matching.gale_shapley(p)
    assert good.assignment == {"S1": "U1", "S2": "U0"} and metrics.blocking_pairs(good, p) == []


def test_capacity_and_zero_capacity():
    u0, u1 = uni("U0", cap=0), uni("U1", cap=2)
    students = [mk(f"S{i}", gpa=3.0 + i / 10, wishes=("U0", "U1")) for i in range(3)]
    for algo in matching.ALGORITHMS:
        res, p = solve([u0, u1], students, algo=algo)
        assert metrics.violations(res, p) == []
        assert sorted(v for v in res.assignment.values() if v) == ["U1", "U1"]
        assert res.assignment["S0"] is None  # le moins bon score reste sans place


def test_replay_and_order_independence():
    unis, students = generator.generate("nominal", n_students=400, n_unis=50)
    for algo in matching.ALGORITHMS:
        h = solve(unis, students, algo=algo)[0].output_hash()
        assert solve(unis, students, algo=algo)[0].output_hash() == h
        su, ss = unis[:], students[:]
        random.Random(3).shuffle(su), random.Random(4).shuffle(ss)
        assert solve(su, ss, algo=algo)[0].output_hash() == h, algo


def test_explanation_answers_why_not_previous_wish():
    unis, students = generator.generate("oversubscribed", n_students=300, n_unis=40)
    res, p = solve(unis, students)
    s = next(s for s in students if res.assignment[s.id] and s.wishes.index(res.assignment[s.id]) >= 2)
    ex = metrics.explain(s, res, p)
    got = s.wishes.index(res.assignment[s.id])
    assert ex[got]["status"] == "assigned"
    assert all(e["status"] in ("rejected", "ineligible") for e in ex[:got])
    assert all(e["status"] == "not_considered" for e in ex[got + 1 :])
    for e in ex[:got]:
        if e["status"] == "rejected":
            assert e["cutoff"] is not None and e["score"] <= e["cutoff"]


# ── corrections issues de la relecture ────────────────────────────────────────
def test_english_scale_is_equitable_between_tests():
    assert english.pct("TOEIC", 945) == english.pct("IELTS", 7.0) == 80.0  # début de C1 dans les deux tests
    assert english.pct("TOEIC", 785) == english.pct("IELTS", 5.5) == 60.0  # début de B2
    assert english.cefr("TOEIC", 990) == "C1" and english.pct("TOEIC", 990) == 100.0  # le TOEIC n'atteste pas le C2
    assert english.cefr("IELTS", 9.0) == "C2" and english.pct("IELTS", 9.0) == 100.0
    assert english.pct("TOEIC", 10) == 0.0 and english.cefr("TOEIC", 100) == "A1"
    pts = [english.pct("TOEIC", x) for x in range(10, 991, 5)]
    assert pts == sorted(pts)


def test_cefr_constant_threshold_in_letters():
    cfg = copy.deepcopy(CFG)
    cfg["eliminatory"][1] = {"key": "english_cefr", "op": ">=", "value": "C1"}
    s = mk("S1", toeic=800)  # B2
    assert rules.failed_thresholds(s, uni("U0"), cfg)[0]["threshold"] == "C1"
    s.english_score = 950.0
    assert rules.failed_thresholds(s, uni("U0"), cfg) == []


def test_university_attribute_threshold_without_code():
    cfg = copy.deepcopy(CFG)
    cfg["eliminatory"].append({"key": "associative", "op": ">=", "ref": "min_associative"})
    u_strict, u_free = uni("U0"), uni("U1")
    u_strict.attributes["min_associative"] = 70
    s = mk("S1", assoc=40, wishes=("U0", "U1"))
    res, p = solve([u_strict, u_free], [s], cfg)
    assert (
        p.reasons[("S1", "U0")][0]["ref"] == "min_associative" and p.reasons[("S1", "U1")] == []
    )  # U1 n'a pas ce seuil
    assert res.assignment["S1"] == "U1"


def test_overrides_make_universities_rank_differently():
    cfg = copy.deepcopy(CFG)
    cfg["overrides"] = {"U1": {"criteria": [{"key": "english_pct", "weight": 1, "min": 0, "max": 100}]}}
    scholar, speaker = (
        mk("S1", gpa=3.9, toeic=600, wishes=("U0", "U1")),
        mk("S2", gpa=2.5, toeic=980, wishes=("U0", "U1")),
    )
    p = matching.Problem([uni("U0"), uni("U1")], [scholar, speaker], cfg)
    assert p.rank["U0"]["S1"] < p.rank["U0"]["S2"] and p.rank["U1"]["S2"] < p.rank["U1"]["S1"]
    assert p.score[("S1", "U0")] != p.score[("S1", "U1")]
    res = matching.gale_shapley(p)
    assert res.assignment == {"S1": "U0", "S2": "U1"} and metrics.blocking_pairs(res, p) == []


def test_lottery_tie_break_is_seeded_and_order_independent():
    a, b = mk("S1"), mk("S2")  # profils identiques
    generator.draw_lottery([b, a], seed=5)
    assert a.attributes["lottery"] != b.attributes["lottery"]
    c, d = mk("S1"), mk("S2")
    generator.draw_lottery([c, d], seed=5)
    assert (c.attributes["lottery"], d.attributes["lottery"]) == (a.attributes["lottery"], b.attributes["lottery"])
    winner = min((a, b), key=lambda s: s.attributes["lottery"]).id
    res, _ = solve([uni("U0")], [a, b])
    assert res.assignment[winner] == "U0"


def test_input_validation():
    for bad in ([mk("S1", wishes=("U0", "U0"))], [mk("S1", wishes=("U0", "U9"))]):
        try:
            matching.Problem([uni("U0")], bad, CFG)
        except ValueError as e:
            assert "entrées invalides" in str(e)
        else:
            raise AssertionError("entrées invalides acceptées")
    res, p = solve([uni("U0", cap=0)], [mk("S1")])
    assert metrics.summarize(res, p)["fill_rate"] is None and res.assignment["S1"] is None


def test_config_id_ignores_name_and_number_type():
    a, b = copy.deepcopy(CFG), copy.deepcopy(CFG)
    b["name"], b["criteria"][0]["weight"] = "autre nom", 0.5  # 0.5 déjà ; on force int/float ailleurs
    b["criteria"][0]["min"] = 0.0
    assert rules.config_id(a) == rules.config_id(b)


def test_golden_hashes_pin_engine_behaviour():
    """Empreintes de référence : si elles changent, le moteur a changé de comportement ⇒ incrémenter ENGINE_VERSION,
    mettre à jour ces valeurs, et savoir que les anciens runs ne se rejoueront plus à l'identique."""
    from engine import ENGINE_VERSION

    unis, students = generator.generate("nominal")
    generator.draw_lottery(students, 42)
    res, _ = solve(unis, students)
    assert (ENGINE_VERSION, generator.dataset_hash(unis, students), res.output_hash()) == (
        "1.0.0",
        "07c99f5f367c5f32",
        "8d3822f1957c1f63",
    )


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ok   {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAIL {name}: {type(e).__name__}: {e}")
    print(f"{len(tests) - failed}/{len(tests)} tests réussis")
    sys.exit(1 if failed else 0)
