"""Shared test fixtures for the entire test suite."""
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# ── In-memory SQLite for tests ────────────────────────────────────────────────
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop them after."""
    # Import models so metadata is populated
    import app.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Minimal valid task payload ────────────────────────────────────────────────

VALID_TASK_PAYLOAD = {
    "title": "Default Task",
    "description": "Default description for testing.",
    "status": "Todo",
    "priority": "Medium",
    "department": "Engineering",
    "team": "Backend Team",
    "assignee": "Alice Smith",
    "created_by": "admin",
    "due_date": "2025-12-31",
    "story_points": 3,
    "estimated_hours": 8,
    "actual_hours": 0,
    "progress_percentage": 0,
    "attachments_count": 0,
    "comments_count": 0,
    "watchers_count": 1,
    "sprint": "Sprint-1",
    "quarter": "Q4",
    "risk_level": "Low",
    "customer_impact": "None",
    "sla_hours": 48,
    "dependencies": [],
    "tags": ["backend", "api"],
}


@pytest.fixture
def make_task(client):
    """Factory fixture: create a task via POST /api/v1/tasks/."""

    def _make_task(**overrides):
        payload = {**VALID_TASK_PAYLOAD, **overrides}
        resp = client.post("/api/v1/tasks/", json=payload)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make_task
