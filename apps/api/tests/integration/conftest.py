from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models  # noqa: F401  (registra as tabelas)
from app.clock import get_today
from app.db import Base, SessionLocal, engine
from app.main import app
from app.seed import seed

FRIDAY = date(2026, 10, 9)


@pytest.fixture(scope="session", autouse=True)
def schema():
    assert engine.url.database.endswith("_test"), "testes de integração só rodam em database *_test"
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def db():
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    with SessionLocal() as session:
        seed(session)
        yield session


class Clock:
    def __init__(self, today: date):
        self.today = today


@pytest.fixture
def clock():
    return Clock(FRIDAY)


@pytest.fixture
def client(db, clock):
    app.dependency_overrides[get_today] = lambda: clock.today
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
