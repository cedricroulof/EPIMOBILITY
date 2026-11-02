"""Orchestration : base ↔ moteur. `load_inputs` (mapping base → moteur) est le contrat du rejeu (§6)."""

import hashlib
import json
import os
import random
import time

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

import generator
from engine import ENGINE_VERSION, algorithms, rules
from engine.algorithms import metrics

from . import db as m
from .auth import hash_password

DEMO_STUDENTS = 3


def seed(db, n_students=1000, n_unis=100, seed=42, password=None) -> None:
    """Jeu de démo chargé au premier démarrage : cohorte générée, configuration par défaut, comptes de démo."""
    if db.scalar(select(func.count()).select_from(m.University)):
        return
    password = password or os.environ.get("DEMO_PASSWORD") or (None if _production() else "demo1234")
    if password is None:
        raise RuntimeError("DEMO_PASSWORD est obligatoire en production")
    unis, students = generator.generate("nominal", n_students, n_unis, seed)
    db.add_all(
        m.University(
            id=u.id,
            name=u.name,
            continent=u.continent,
            capacity=u.capacity,
            min_gpa=u.min_gpa,
            min_cefr=u.min_cefr,
            selectivity=u.selectivity,
            attributes=u.attributes,
        )
        for u in unis
    )
    db.flush()
    for s in students:
        db.add(
            m.Student(
                id=s.id,
                gpa=s.gpa,
                english_test=s.english_test,
                english_score=s.english_score,
                associative=s.associative,
                attributes=s.attributes,
                wishes=[m.Wish(rank=i + 1, university_id=u) for i, u in enumerate(s.wishes)],
            )
        )
    cfg = rules.DEFAULT_CONFIG
    db.add(m.RuleConfig(id=rules.config_id(cfg), name=cfg["name"], config=cfg))
    pw = hash_password(password)
    db.add(m.User(email="admin@exemple.test", password_hash=pw, role="admin"))
    for i in range(DEMO_STUDENTS):
        db.add(
            m.User(email=f"etudiant{i + 1}@exemple.test", password_hash=pw, role="student", student_id=students[i].id)
        )
    db.commit()


def _production() -> bool:
    return os.environ.get("APP_ENV", "development") == "production"


def attribute_keys(db) -> tuple[set, set]:
    s_keys = {k for a in db.scalars(select(m.Student.attributes)) for k in a}
    u_keys = {k for a in db.scalars(select(m.University.attributes)) for k in a}
    return s_keys, u_keys


def load_inputs(db) -> tuple[list, list]:
    """État courant de la base → objets du moteur, triés par id : l'ordre des lignes n'influence jamais le résultat."""
    unis = [
        generator.University(
            u.id, u.name, u.continent, u.capacity, u.min_gpa, u.min_cefr, u.selectivity, dict(u.attributes)
        )
        for u in db.scalars(select(m.University).order_by(m.University.id))
    ]
    students = [
        generator.Student(
            s.id,
            s.gpa,
            s.english_test,
            s.english_score,
            s.associative,
            [w.university_id for w in s.wishes],
            dict(s.attributes),
        )
        for s in db.scalars(select(m.Student).order_by(m.Student.id).options(selectinload(m.Student.wishes)))
    ]
    return unis, students


def from_snapshot(snapshot: str) -> tuple[list, list]:
    data = json.loads(snapshot)
    return (
        [generator.University(**u) for u in data["universities"]],
        [generator.Student(**s) for s in data["students"]],
    )


def execute(db, config: m.RuleConfig, algorithm: str, seed: int | None, inputs, replay_of=None) -> m.Run:
    """Snapshot → moteur → persistance, en une transaction. ValueError si la configuration ne colle pas aux données."""
    seed = random.randrange(2**31) if seed is None else seed
    unis, students = inputs
    generator.draw_lottery(students, seed)  # au snapshot : le rejeu relit les mêmes numéros
    snapshot = generator.snapshot(unis, students)
    t0 = time.perf_counter()
    problem = algorithms.Problem(unis, students, config.config)
    result = algorithms.ALGORITHMS[algorithm](problem)
    summary = metrics.summarize(result, problem)
    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    run = m.Run(
        config_id=config.id,
        algorithm=algorithm,
        seed=seed,
        engine_version=ENGINE_VERSION,
        input_snapshot=snapshot,
        input_hash=hashlib.sha256(snapshot.encode()).hexdigest()[:16],
        output_hash=result.output_hash(),
        metrics=summary,
        duration_ms=duration_ms,
        replay_of=replay_of,
    )
    db.add(run)
    db.flush()
    for s in students:
        u = result.assignment[s.id]
        db.add(
            m.Assignment(
                run_id=run.id,
                student_id=s.id,
                university_id=u,
                rank=s.wishes.index(u) + 1 if u else None,
                explanation=metrics.explain(s, result, problem),
            )
        )
    db.commit()
    return run


def run_view(run: m.Run) -> dict:
    keys = (
        "id",
        "config_id",
        "algorithm",
        "seed",
        "engine_version",
        "input_hash",
        "output_hash",
        "metrics",
        "duration_ms",
        "created_at",
        "published_at",
        "replay_of",
    )
    return {k: getattr(run, k) for k in keys}
