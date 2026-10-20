"""Test setup: a real Postgres database, separate from your dev data.

Tests run against TEST_DATABASE_URL (from the environment or backend/.env).
Every table is emptied after each test, so the database name MUST end in
"_test". That rule stops a typo from wiping your real data.
"""
import os
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

BACKEND = Path(__file__).resolve().parent.parent
TEST_URL = os.environ.get("TEST_DATABASE_URL") or dotenv_values(BACKEND / ".env").get("TEST_DATABASE_URL")

if not TEST_URL:
    pytest.exit("TEST_DATABASE_URL is not set. Add it to backend/.env (see .env.example).", 2)
if not (make_url(TEST_URL).database or "").endswith("_test"):
    pytest.exit("Refusing to run: the test database name must end in '_test'.", 2)

# Point the app at the test database BEFORE any app module is imported.
os.environ["DATABASE_URL"] = TEST_URL

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Build the tables once, using the real migrations (so they get tested too)."""
    command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def empty_tables():
    yield
    names = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} CASCADE"))


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def event(client):
    """A ready-made event for tests that need one."""
    response = client.post("/admin/events", json={
        "slug": "testcon", "name": "TestCon",
        "starts_at": "2027-04-16T08:00:00-05:00", "ends_at": "2027-04-16T17:00:00-05:00",
    })
    assert response.status_code == 201
    return response.json()
