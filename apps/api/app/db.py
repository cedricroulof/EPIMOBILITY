"""Connection and tables (§4 of docs/architecture.md). Invariants enforced by the database stay enforced by it:
5 distinct wishes per student (primary key + unique constraint), one assignment per student and per run."""

import os
from datetime import UTC, datetime

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./epimobility.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)  # naive UTC: same behavior on SQLite and PostgreSQL


def get_db():
    with SessionLocal() as db:
        yield db


class Base(DeclarativeBase):
    type_annotation_map = {dict: JSON, list: JSON}


class University(Base):
    __tablename__ = "universities"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    continent: Mapped[str]
    capacity: Mapped[int] = mapped_column(CheckConstraint("capacity >= 0"))
    min_gpa: Mapped[float]
    min_cefr: Mapped[str]
    selectivity: Mapped[float]
    attributes: Mapped[dict] = mapped_column(default=dict)


class Student(Base):
    __tablename__ = "students"
    id: Mapped[str] = mapped_column(primary_key=True)
    gpa: Mapped[float]
    english_test: Mapped[str]
    english_score: Mapped[float]
    associative: Mapped[int]
    attributes: Mapped[dict] = mapped_column(default=dict)
    wishes: Mapped[list["Wish"]] = relationship(order_by="Wish.rank", cascade="all, delete-orphan")


class Wish(Base):
    __tablename__ = "wishes"
    __table_args__ = (UniqueConstraint("student_id", "university_id"), CheckConstraint("rank BETWEEN 1 AND 5"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), primary_key=True)
    rank: Mapped[int] = mapped_column(primary_key=True)
    university_id: Mapped[str] = mapped_column(ForeignKey("universities.id"))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(CheckConstraint("role IN ('student', 'admin')"))
    student_id: Mapped[str | None] = mapped_column(ForeignKey("students.id"), unique=True)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(primary_key=True)  # never the plain-text token (ADR-0005)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime]
    user: Mapped[User] = relationship(lazy="joined")


class RuleConfig(Base):
    __tablename__ = "rule_configs"
    id: Mapped[str] = mapped_column(primary_key=True)  # content hash: immutable, modifying = new row
    name: Mapped[str]
    config: Mapped[dict]
    created_at: Mapped[datetime] = mapped_column(default=now)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    config_id: Mapped[str] = mapped_column(ForeignKey("rule_configs.id"))
    algorithm: Mapped[str]
    seed: Mapped[int]
    engine_version: Mapped[str]
    input_snapshot: Mapped[str] = mapped_column(Text)  # canonical JSON, byte for byte: basis of the replay (ADR-0003)
    input_hash: Mapped[str]
    output_hash: Mapped[str]
    metrics: Mapped[dict]
    duration_ms: Mapped[float]
    created_at: Mapped[datetime] = mapped_column(default=now)
    published_at: Mapped[datetime | None]
    replay_of: Mapped[int | None] = mapped_column(ForeignKey("runs.id"))


class Assignment(Base):
    __tablename__ = "assignments"
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), primary_key=True)
    university_id: Mapped[str | None] = mapped_column(ForeignKey("universities.id"))
    rank: Mapped[int | None]
    explanation: Mapped[list]
