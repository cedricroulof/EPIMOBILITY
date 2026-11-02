"""Tests unitaires du générateur : reproductibilité (seed), bornes réalistes, couverture des continents, scénarios."""

import generator


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
