"""REST API (§7 of docs/architecture.md), under /api: web and mobile are two clients of it. OpenAPI at /docs."""

from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from pydantic import AfterValidator, BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session as OrmSession

from engine import ENGINE_VERSION, algorithms, rules

from . import auth, services
from . import db as m
from .auth import COOKIE, SECURE_COOKIE, SESSION_TTL, current_user, require_role
from .db import get_db


@asynccontextmanager
async def lifespan(_app):
    # ponytail: create_all at startup; switch to Alembic as soon as a deployed schema has to evolve
    m.Base.metadata.create_all(m.engine)
    with m.SessionLocal() as db:
        services.seed(db)
    yield


app = FastAPI(title="EPIMOBILITY API", version="0.1.0", lifespan=lifespan)
api = APIRouter(prefix="/api")
Db = Annotated[OrmSession, Depends(get_db)]
Student = Annotated[m.User, Depends(require_role("student"))]
Admin = Annotated[m.User, Depends(require_role("admin"))]


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.update(
        {"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin"}
    )
    if SECURE_COOKIE:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


# ── public ───────────────────────────────────────────────────────────────────
@api.get("/health")
def health(db: Db):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "api_version": app.version, "engine_version": ENGINE_VERSION}


class LoginIn(BaseModel):
    email: str
    password: str


@api.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, db: Db):
    token, user = auth.login(db, body.email, body.password, request.client.host if request.client else "?")
    response.set_cookie(
        COOKIE, token, max_age=int(SESSION_TTL.total_seconds()), httponly=True, samesite="lax", secure=SECURE_COOKIE
    )
    return {"token": token, "role": user.role}


@api.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: Db):
    auth.logout(db, request)
    response.delete_cookie(COOKIE)


@api.get("/me")
def me(user: Annotated[m.User, Depends(current_user)]):
    return {"email": user.email, "role": user.role, "student_id": user.student_id}


# ── catalogue ────────────────────────────────────────────────────────────────
def _uni(u: m.University) -> dict:
    return {k: getattr(u, k) for k in ("id", "name", "continent", "capacity", "min_gpa", "min_cefr", "attributes")}


@api.get("/universities", dependencies=[Depends(current_user)])
def universities(db: Db, continent: str | None = None):
    q = select(m.University).order_by(m.University.id)
    if continent:
        q = q.where(m.University.continent == continent)
    return [_uni(u) for u in db.scalars(q)]


@api.get("/universities/{uni_id}", dependencies=[Depends(current_user)])
def university(uni_id: str, db: Db):
    if (u := db.get(m.University, uni_id)) is None:
        raise HTTPException(404, "Unknown university")
    return _uni(u)


# ── student area: no route takes a student identifier, everything goes through the session ──
def _distinct(ids: list[str]) -> list[str]:
    if len(set(ids)) != len(ids):
        raise ValueError("the 5 wishes must be distinct")
    return ids


class WishesIn(BaseModel):
    wishes: Annotated[list[str], Field(min_length=5, max_length=5), AfterValidator(_distinct)]


def _published(db):
    return db.scalar(select(m.Run).where(m.Run.published_at.is_not(None)).order_by(m.Run.published_at.desc()))


@api.get("/me/wishes")
def get_wishes(user: Student, db: Db):
    return {"wishes": [w.university_id for w in db.get(m.Student, user.student_id).wishes]}


@api.put("/me/wishes")
def put_wishes(body: WishesIn, user: Student, db: Db):
    # ponytail: wishes closed as soon as a run is published; admin `wishes_open` setting when reopening is requested
    if _published(db):
        raise HTTPException(409, "Wishes are closed: the results are published")
    unknown = set(body.wishes) - set(db.scalars(select(m.University.id).where(m.University.id.in_(body.wishes))))
    if unknown:
        raise HTTPException(422, f"Unknown universities: {sorted(unknown)}")
    student = db.get(m.Student, user.student_id)
    student.wishes.clear()
    db.flush()
    student.wishes.extend(m.Wish(rank=i + 1, university_id=u) for i, u in enumerate(body.wishes))
    db.commit()
    return {"wishes": body.wishes}


@api.get("/me/result")
def my_result(user: Student, db: Db):
    if (run := _published(db)) is None:
        raise HTTPException(404, "No published result")
    a = db.get(m.Assignment, (run.id, user.student_id))
    return {"run_id": run.id, "university_id": a.university_id, "rank": a.rank, "explanation": a.explanation}


# ── admin area ───────────────────────────────────────────────────────────────
@api.get("/admin/configs")
def list_configs(_: Admin, db: Db):
    return [{"id": c.id, "name": c.name, "config": c.config} for c in db.scalars(select(m.RuleConfig))]


@api.post("/admin/configs", status_code=201)
def create_config(config: dict, _: Admin, db: Db, response: Response):
    """Idempotent: same content ⇒ same version (200). All errors are returned at once (422)."""
    s_keys, u_keys = services.attribute_keys(db)
    try:
        rules.validate(config, student_keys=s_keys, university_keys=u_keys)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    cid = rules.config_id(config)
    if (existing := db.get(m.RuleConfig, cid)) is None:
        existing = m.RuleConfig(id=cid, name=config.get("name", cid), config=config)
        db.add(existing)
        db.commit()
    else:
        response.status_code = 200
    return {"id": existing.id, "name": existing.name}


class RunIn(BaseModel):
    config_id: str
    algorithm: Literal[tuple(algorithms.ALGORITHMS)]  # type: ignore[valid-type]
    seed: int | None = None


def _run(db, run_id: int) -> m.Run:
    if (run := db.get(m.Run, run_id)) is None:
        raise HTTPException(404, "Unknown run")
    return run


def _execute(db, config_id, algorithm, seed, inputs, replay_of=None):
    if (config := db.get(m.RuleConfig, config_id)) is None:
        raise HTTPException(404, "Unknown configuration")
    try:
        return services.execute(db, config, algorithm, seed, inputs, replay_of)
    except ValueError as e:
        db.rollback()
        raise HTTPException(422, str(e)) from None


@api.post("/admin/runs", status_code=201)
def create_run(body: RunIn, _: Admin, db: Db):
    return services.run_view(_execute(db, body.config_id, body.algorithm, body.seed, services.load_inputs(db)))


@api.get("/admin/runs")
def list_runs(_: Admin, db: Db):
    return [services.run_view(r) for r in db.scalars(select(m.Run).order_by(m.Run.id.desc()))]


@api.get("/admin/runs/{run_id}")
def get_run(run_id: int, _: Admin, db: Db):
    return services.run_view(_run(db, run_id))


@api.post("/admin/runs/{run_id}/replay", status_code=201)
def replay(run_id: int, _: Admin, db: Db):
    """Replays from the stored snapshot, regardless of the current state of the database."""
    orig = _run(db, run_id)
    new = _execute(db, orig.config_id, orig.algorithm, orig.seed, services.from_snapshot(orig.input_snapshot), orig.id)
    return {
        "run": services.run_view(new),
        "identical": new.output_hash == orig.output_hash,
        "engine_version": {"original": orig.engine_version, "current": new.engine_version},
    }


@api.post("/admin/runs/{run_id}/publish")
def publish(run_id: int, _: Admin, db: Db):
    run = _run(db, run_id)
    if run.algorithm != "gale_shapley":
        raise HTTPException(409, "Only a Gale-Shapley (stable) run can be published")
    run.published_at = m.now()
    db.commit()
    return services.run_view(run)


@api.get("/admin/runs/{a}/compare/{b}")
def compare(a: int, b: int, _: Admin, db: Db):
    """What-if mode: metrics side by side and students whose assignment changes."""
    ra, rb = _run(db, a), _run(db, b)
    q = select(m.Assignment.student_id, m.Assignment.university_id)
    xa, xb = (dict(db.execute(q.filter_by(run_id=r)).all()) for r in (a, b))
    moved = [{"student_id": s, "a": xa[s], "b": xb.get(s)} for s in sorted(xa) if xa[s] != xb.get(s)]
    return {"a": services.run_view(ra), "b": services.run_view(rb), "moved": moved}


app.include_router(api)
