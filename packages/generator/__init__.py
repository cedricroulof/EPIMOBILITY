"""Génération reproductible (seed) d'universités et d'étudiants fictifs, avec scénarios de tension.

Tout passe par une instance `random.Random(seed)`, jamais le module global : même seed ⇒ même jeu
de données octet pour octet (vérifié par `dataset_hash` dans les tests et le bench).
Les 100 universités réelles viendront d'un fichier de données sourcé ; ici elles sont synthétiques
mais *cohérentes* : une université sélective a peu de places et des seuils élevés.
"""

import hashlib
import itertools
import json
import random
from dataclasses import asdict, dataclass, field

from engine.rules import english
from engine.rules.english import CEFR  # noqa: F401  (réexport : l'indice sert d'ordinal)

CONTINENTS = ["Europe", "Asie", "Afrique", "Amérique du Nord", "Amérique du Sud", "Océanie"]
CONTINENT_WEIGHTS = [45, 20, 5, 15, 7, 8]
TESTS = {"TOEIC": (10, 990), "IELTS": (0.0, 9.0)}


@dataclass
class University:
    id: str
    name: str
    continent: str
    capacity: int
    min_gpa: float
    min_cefr: str
    selectivity: float  # 0..1, fictif : pilote la cohérence places/seuils et la demande
    attributes: dict = field(default_factory=dict)  # seuils ajoutés sans code côté université (ex. min_associative)


@dataclass
class Student:
    id: str
    gpa: float  # 0..4
    english_test: str  # TOEIC | IELTS
    english_score: float
    associative: int  # 0..100
    wishes: list  # 5 ids d'universités, ordonnés (vœu 1 en premier)
    attributes: dict = field(default_factory=dict)  # critères ajoutés sans code (projet perso, absences…)

    @property
    def english_cefr(self) -> str:
        return english.cefr(self.english_test, self.english_score)

    @property
    def english_pct(self) -> float:
        return english.pct(self.english_test, self.english_score)


SCENARIOS = {
    "nominal": "distributions réalistes, capacité totale ≈ 1,1 × effectif",
    "oversubscribed": "60 % des étudiants concentrent leurs vœux sur les 10 universités les plus prisées",
    "weak_english": "cohorte faible en anglais (TOEIC moyen 560) : beaucoup d'inéligibles",
    "tight_capacity": "capacités réduites à 80 % : moins de places que d'étudiants",
    "abundant": "capacités triplées : chacun devrait obtenir un bon vœu",
    "ties": "tous les étudiants ont le même profil : seul le départage (tirage au sort seedé) décide",
}


def make_universities(n=100, seed=42):
    rng = random.Random(seed)
    unis = []
    for i in range(n):
        sel = rng.betavariate(2, 3)
        continent = CONTINENTS[i] if i < len(CONTINENTS) else rng.choices(CONTINENTS, CONTINENT_WEIGHTS)[0]
        unis.append(
            University(
                id=f"U{i:03d}",
                name=f"Université fictive {i:03d}",
                continent=continent,
                capacity=round(3 + (1 - sel) * 14),
                min_gpa=round(2.0 + sel * 1.5, 1),
                min_cefr="C1" if sel > 0.8 else "B2" if sel > 0.4 else "B1",
                selectivity=round(sel, 3),
            )
        )
    return unis


def generate(scenario="nominal", n_students=1000, n_unis=100, seed=42):
    """Retourne (universités, étudiants) pour un scénario. Déterministe pour (scenario, n_students, n_unis, seed)."""
    if scenario not in SCENARIOS:
        raise ValueError(f"scénario inconnu {scenario!r}, attendu : {sorted(SCENARIOS)}")
    unis = make_universities(n_unis, seed)
    if scenario == "tight_capacity":
        for u in unis:
            u.capacity = max(1, round(u.capacity * 0.8))
    if scenario == "abundant":
        for u in unis:
            u.capacity *= 3

    rng = random.Random(seed)
    ids = [u.id for u in unis]
    popularity = [0.5 + 1.5 * u.selectivity for u in unis]  # prestige ⇒ demande
    by_id = {u.id: u for u in unis}
    top10 = set(sorted(range(n_unis), key=lambda i: -popularity[i])[:10])
    hot = [w * (20 if i in top10 else 1) for i, w in enumerate(popularity)]
    cum_pop, cum_hot = list(itertools.accumulate(popularity)), list(itertools.accumulate(hot))
    weak = scenario == "weak_english"

    students = []
    for i in range(n_students):
        if scenario == "ties":
            gpa, test, score, assoc = 3.0, "TOEIC", 800.0, 50
        else:
            gpa = round(min(4.0, max(1.0, rng.gauss(2.9, 0.5))), 2)
            if rng.random() < 0.6:
                test, score = "TOEIC", 5 * round(min(990, max(250, rng.gauss(560 if weak else 720, 150))) / 5)
            else:
                test, score = "IELTS", 0.5 * round(min(9.0, max(3.0, rng.gauss(5.2 if weak else 6.3, 1.0))) / 0.5)
            assoc = int(min(100, max(0, rng.gauss(50, 20))))
        cum = cum_hot if scenario == "oversubscribed" and rng.random() < 0.6 else cum_pop
        st = Student(f"S{i:05d}", gpa, test, float(score), assoc, [])
        st.wishes = _wishes(rng, st, by_id, ids, cum, 5)
        students.append(st)
    return unis, students


def _wishes(rng, student, by_id, ids, cum_weights, k, dream=0.15):
    """k vœux distincts, tirés selon la popularité, avec auto-sélection : un vœu où l'étudiant est inéligible
    n'est conservé qu'avec probabilité `dream` (vœu « de rêve »). Les étudiants réels visent surtout l'accessible."""
    level = CEFR.index(student.english_cefr)
    picked = []
    for _ in range(50):  # borne de sécurité : jamais de boucle infinie, même sur un profil très faible
        for x in rng.choices(ids, cum_weights=cum_weights, k=k):
            u = by_id[x]
            if x in picked or ((student.gpa < u.min_gpa or level < CEFR.index(u.min_cefr)) and rng.random() > dream):
                continue
            picked.append(x)
            if len(picked) == k:
                return picked
    return picked + [x for x in ids if x not in picked][: k - len(picked)]


def draw_lottery(students, seed):
    """Numéro de tirage au sort par étudiant (départage ultime, config `tie_break` clé `lottery`).
    Tiré dans l'ordre des ids ⇒ indépendant de l'ordre des lignes ; à faire AU SNAPSHOT, avec `run.seed`, pour que le rejeu
    relise les mêmes numéros. Ne réécrit pas un numéro déjà présent."""
    rng = random.Random(seed)
    for s in sorted(students, key=lambda s: s.id):
        s.attributes.setdefault("lottery", round(rng.random(), 9))
    return students


def snapshot(unis, students) -> str:
    """Sérialisation canonique du jeu d'entrée : c'est ce que l'API stocke dans un run pour le rejeu."""
    return json.dumps(
        {"universities": [asdict(u) for u in unis], "students": [asdict(s) for s in students]},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def dataset_hash(unis, students) -> str:
    return hashlib.sha256(snapshot(unis, students).encode()).hexdigest()[:16]
