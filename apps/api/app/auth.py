"""Opaque sessions (ADR-0005): random token stored hashed, carried in a cookie (web) or as a Bearer token (mobile)."""

import hashlib
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from .db import Session, User, get_db, now

SESSION_TTL = timedelta(days=7)
COOKIE = "session"
SECURE_COOKIE = os.environ.get("APP_ENV", "development") == "production"
MAX_FAILURES, WINDOW_S = 5, 60

_hasher = PasswordHasher()  # argon2id, RFC 9106 parameters
_DUMMY_HASH = _hasher.hash("timing-equalizer")
# ponytail: in-memory, per-process counter; move it to the database if the API runs on several instances
_failures: dict[tuple[str, str], deque] = defaultdict(deque)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def login(db, email: str, password: str, client_ip: str) -> tuple[str, User]:
    key, t = (client_ip, email.lower()), time.monotonic()
    fails = _failures[key]
    while fails and t - fails[0] > WINDOW_S:
        fails.popleft()
    if len(fails) >= MAX_FAILURES:
        raise HTTPException(429, "Too many attempts, try again in a minute")
    user = db.scalar(select(User).where(User.email == email.lower()))
    try:
        _hasher.verify(user.password_hash if user else _DUMMY_HASH, password)  # same duration, known account or not
        if user is None:
            raise VerifyMismatchError
    except VerifyMismatchError:
        fails.append(t)
        raise HTTPException(401, "Incorrect email or password") from None
    fails.clear()
    token = secrets.token_urlsafe(32)
    db.add(Session(token_hash=_token_hash(token), user_id=user.id, expires_at=now() + SESSION_TTL))
    db.commit()
    return token, user


def _token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    return header[7:] if header.lower().startswith("bearer ") else request.cookies.get(COOKIE)


def logout(db, request: Request) -> None:
    if token := _token(request):
        db.query(Session).filter_by(token_hash=_token_hash(token)).delete()
        db.commit()


def current_user(request: Request, db: Annotated[OrmSession, Depends(get_db)]) -> User:
    token = _token(request)
    session = db.get(Session, _token_hash(token)) if token else None
    if session is None or session.expires_at < now():
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    session.expires_at = now() + SESSION_TTL  # sliding expiration
    db.commit()
    return session.user


def require_role(role: str):
    def check(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role != role:
            raise HTTPException(403, "Access denied")
        return user

    return check
