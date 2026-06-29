"""Shared test fixtures for the entire test suite."""

import os
import sys
import uuid
from pathlib import Path

# Ensure backend root is on sys.path before importing test support modules.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from tests.support.db_env import (
    assert_safe_test_database_url,
    derive_admin_database_url,
    ensure_database_exists,
    load_supabase_database_url,
    load_test_database_url,
    test_mode_allows_remote_database,
)

TEST_SCHEMA = f"test_{uuid.uuid4().hex}"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_FILES = (BACKEND_ROOT / ".env", PROJECT_ROOT / ".env")


DATABASE_URL = load_test_database_url(os.environ, ENV_FILES)
ALLOW_REMOTE_TEST_DATABASE = test_mode_allows_remote_database()
PARSED_TEST_DATABASE_URL = assert_safe_test_database_url(
    DATABASE_URL,
    allow_remote=ALLOW_REMOTE_TEST_DATABASE,
)
SUPABASE_DATABASE_URL = load_supabase_database_url(os.environ, ENV_FILES)
TEST_DATABASE_ADMIN_URL = derive_admin_database_url(
    DATABASE_URL,
    os.environ.get("TEST_DATABASE_ADMIN_URL"),
)

if not ALLOW_REMOTE_TEST_DATABASE:
    ensure_database_exists(DATABASE_URL, TEST_DATABASE_ADMIN_URL)

os.environ["DATABASE_URL"] = DATABASE_URL
os.environ["DATABASE_SCHEMA"] = TEST_SCHEMA

bootstrap_engine = create_engine(DATABASE_URL)
with bootstrap_engine.begin() as connection:
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{TEST_SCHEMA}"'))
bootstrap_engine.dispose()

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

# ── In-memory SQLite for tests ────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"options": f"-csearch_path={TEST_SCHEMA}"},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_test_hierarchy(db):
    """Seed a default department, team, user, project and membership for testing."""
    from app.core.security import get_password_hash
    from app.db.models.department import Department
    from app.db.models.project import Project
    from app.db.models.project_member import ProjectMember
    from app.db.models.team import Team
    from app.db.models.user import User

    # Check if already seeded in this transaction to avoid duplicates
    existing_dept = (
        db.query(Department).filter(Department.name == "Engineering").first()
    )
    if existing_dept:
        admin = db.query(User).filter(User.username == "admin").first()
        worker = db.query(User).filter(User.username == "worker").first()
        project = db.query(Project).filter(Project.key == "PRJ").first()
        return {
            "dept_id": existing_dept.id,
            "team_id": project.team_id,
            "admin": admin,
            "worker": worker,
            "project_id": project.id,
        }

    dept = Department(name="Engineering", description="Engineering Dept")
    db.add(dept)
    db.flush()

    team = Team(
        name="Backend Team", department_id=dept.id, description="Backend development"
    )
    db.add(team)
    db.flush()

    admin = User(
        email="admin@tracker.com",
        username="admin",
        full_name="Administrator",
        hashed_password=get_password_hash("password123"),
        role="admin",
        team_id=team.id,
        is_active=True,
    )
    worker = User(
        email="worker@tracker.com",
        username="worker",
        full_name="Worker User",
        hashed_password=get_password_hash("password123"),
        role="worker",
        team_id=team.id,
        is_active=True,
    )
    db.add_all([admin, worker])
    db.flush()

    project = Project(
        name="Backend Team Project",
        key="PRJ",
        description="Backend project",
        team_id=team.id,
        status="ACTIVE",
    )
    db.add(project)
    db.flush()

    pm1 = ProjectMember(project_id=project.id, user_id=admin.id, project_role="OWNER")
    pm2 = ProjectMember(project_id=project.id, user_id=worker.id, project_role="MEMBER")
    db.add_all([pm1, pm2])
    db.flush()

    return {
        "dept_id": dept.id,
        "team_id": team.id,
        "admin": admin,
        "worker": worker,
        "project_id": project.id,
    }


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Create all tables before each test, drop them after."""
    import app.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_schema():
    yield
    cleanup_engine = create_engine(DATABASE_URL)
    with cleanup_engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA IF EXISTS "{TEST_SCHEMA}" CASCADE'))
    cleanup_engine.dispose()


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
    from app.core.security import get_current_user

    seed = seed_test_hierarchy(db_session)

    def override_get_current_user():
        return seed["admin"]

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as c:
        original_post = c.post

        def wrapped_post(url, *args, **kwargs):
            if url == "/api/v1/tasks/" or url == "/api/v1/tasks":
                if "?" not in url:
                    url = f"{url}?project_id={seed['project_id']}"
                elif "project_id" not in url:
                    url = f"{url}&project_id={seed['project_id']}"

                # Strip deprecated fields from JSON body if present
                if "json" in kwargs and isinstance(kwargs["json"], dict):
                    # Copy to avoid mutating original test data structures
                    kwargs["json"] = kwargs["json"].copy()
                    for f in ["department", "team", "assignee", "created_by", "sprint"]:
                        kwargs["json"].pop(f, None)
            return original_post(url, *args, **kwargs)

        c.post = wrapped_post
        c.seed = seed
        yield c
    app.dependency_overrides.clear()


# ── Minimal valid task payload ────────────────────────────────────────────────

VALID_TASK_PAYLOAD = {
    "title": "Default Task",
    "description": "Default description for testing.",
    "status": "Todo",
    "priority": "Medium",
    "due_date": "2025-12-31",
    "story_points": 3,
    "estimated_hours": 8,
    "actual_hours": 0,
    "progress_percentage": 0,
    "quarter": "Q4",
    "risk_level": "Low",
    "customer_impact": "None",
    "sla_hours": 48,
    "dependencies": [],
    "tags": ["backend", "api"],
}


@pytest.fixture
def make_task(client, db_session):
    """Factory fixture: create a task via POST /api/v1/tasks/."""

    def _make_task(**overrides):
        db = db_session
        project_id = overrides.get("project_id", client.seed["project_id"])

        if "department" in overrides:
            dept_name = overrides["department"]
            from app.db.models.department import Department
            from app.db.models.project import Project
            from app.db.models.project_member import ProjectMember
            from app.db.models.team import Team

            dept = db.query(Department).filter(Department.name == dept_name).first()
            if not dept:
                dept = Department(name=dept_name, description=f"{dept_name} Dept")
                db.add(dept)
                db.flush()

            team = db.query(Team).filter(Team.department_id == dept.id).first()
            if not team:
                team = Team(
                    name=f"{dept_name} Team",
                    department_id=dept.id,
                    description=f"{dept_name} team",
                )
                db.add(team)
                db.flush()

            project = db.query(Project).filter(Project.team_id == team.id).first()
            if not project:
                key = dept_name[:3].upper()
                project = Project(
                    name=f"{dept_name} Project",
                    key=key,
                    team_id=team.id,
                    status="ACTIVE",
                )
                db.add(project)
                db.flush()

                admin = client.seed["admin"]
                pm = ProjectMember(
                    project_id=project.id, user_id=admin.id, project_role="OWNER"
                )
                db.add(pm)
                db.flush()

            project_id = project.id

        assignee_id = None
        if "assignee" in overrides:
            assignee_name = overrides["assignee"]
            from app.db.models.user import User

            user = (
                db.query(User)
                .filter(
                    (User.full_name == assignee_name) | (User.username == assignee_name)
                )
                .first()
            )
            if not user:
                username = assignee_name.lower().replace(" ", "_")
                email = f"{username}@tracker.com"
                user = User(
                    email=email,
                    username=username,
                    full_name=assignee_name,
                    hashed_password="password123",
                    role="worker",
                    team_id=client.seed["team_id"],
                    is_active=True,
                )
                db.add(user)
                db.flush()
            assignee_id = user.id

        payload = {**VALID_TASK_PAYLOAD, **overrides}
        if assignee_id is not None:
            payload["assignee_id"] = assignee_id

        # Pop deprecated fields
        for f in ["department", "team", "assignee", "created_by", "sprint"]:
            payload.pop(f, None)

        resp = client.post(f"/api/v1/tasks/?project_id={project_id}", json=payload)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make_task
