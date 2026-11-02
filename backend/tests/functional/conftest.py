"""API testée en processus (TestClient) sur une base SQLite en mémoire, neuve pour chaque test : isolation totale."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, db, services
from app.main import app

PASSWORD = "demo1234"  # jeu de test uniquement


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    db.Base.metadata.create_all(engine)
    Session = sessionmaker(engine, expire_on_commit=False)
    with Session() as s:
        services.seed(s, n_students=60, n_unis=12, password=PASSWORD)

    def override():
        with Session() as s:
            yield s

    app.dependency_overrides[db.get_db] = override
    auth._failures.clear()
    yield TestClient(app)  # sans `with` : pas de lifespan, la base de test n'est pas remplacée
    app.dependency_overrides.clear()


@pytest.fixture
def login(client):
    def as_user(email):
        r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['token']}"}

    return as_user


@pytest.fixture
def admin(login):
    return login("admin@exemple.test")


@pytest.fixture
def student(login):
    return login("etudiant1@exemple.test")
