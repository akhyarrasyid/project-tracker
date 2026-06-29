import datetime

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.db.session import get_db
from app.main import app
from tests.conftest import seed_test_hierarchy


@pytest.fixture
def project_client(db_session):
    seed_test_hierarchy(db_session)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_projects_admin(project_client, db_session):
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    resp = project_client.get("/api/v1/projects/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_list_projects_worker(project_client, db_session):
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["worker"]

    resp = project_client.get("/api/v1/projects/")
    assert resp.status_code == 200
    # Worker is in seed project
    assert len(resp.json()) >= 1


def test_create_project_admin_success(project_client, db_session):
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    resp = project_client.post(
        "/api/v1/projects/",
        json={
            "name": "New Awesome Project",
            "key": "NEW",
            "description": "Desc",
            "team_id": seed["team_id"],
        },
    )
    assert resp.status_code == 201
    assert resp.json()["key"] == "NEW"

    # Try duplicate key
    resp_dup = project_client.post(
        "/api/v1/projects/",
        json={
            "name": "New Awesome Project 2",
            "key": "NEW",
            "description": "Desc",
            "team_id": seed["team_id"],
        },
    )
    assert resp_dup.status_code == 400
    assert resp_dup.json()["detail"] == "Project with this key already exists"


def test_create_project_worker_forbidden(project_client, db_session):
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["worker"]

    resp = project_client.post(
        "/api/v1/projects/",
        json={
            "name": "Worker Proj",
            "key": "WRK",
            "description": "Desc",
            "team_id": seed["team_id"],
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Only admin users can create projects"


def test_get_project_details(project_client, db_session):
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    resp = project_client.get(f"/api/v1/projects/{seed['project_id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == seed["project_id"]


def test_get_project_tasks(project_client, db_session):
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    resp = project_client.get(f"/api/v1/projects/{seed['project_id']}/tasks")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_project_summary_returns_authoritative_metrics(project_client, db_session):
    from app.db.models.task import Task

    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    today = datetime.date.today()
    tasks = [
        Task(
            title="Done task",
            description="Done",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            due_date=today - datetime.timedelta(days=1),
            status="Done",
            story_points=8,
            estimated_hours=8,
            actual_hours=8,
            progress_percentage=100,
            quarter="Q4",
            risk_level="Low",
            customer_impact="None",
            sla_hours=48,
            dependencies=[],
            tags=[],
            number=1,
        ),
        Task(
            title="Blocked high risk",
            description="Blocked",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            due_date=today + datetime.timedelta(days=2),
            status="In Progress",
            is_blocked=True,
            blocked_reason="Waiting for approval",
            story_points=5,
            estimated_hours=8,
            actual_hours=0,
            progress_percentage=30,
            quarter="Q4",
            risk_level="High",
            customer_impact="None",
            sla_hours=48,
            dependencies=[],
            tags=[],
            number=2,
        ),
        Task(
            title="Overdue todo",
            description="Overdue",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            due_date=today - datetime.timedelta(days=2),
            status="Todo",
            story_points=3,
            estimated_hours=8,
            actual_hours=0,
            progress_percentage=0,
            quarter="Q4",
            risk_level="Low",
            customer_impact="None",
            sla_hours=48,
            dependencies=[],
            tags=[],
            number=3,
        ),
    ]
    db_session.add_all(tasks)
    db_session.commit()

    resp = project_client.get(f"/api/v1/projects/{seed['project_id']}/summary")
    assert resp.status_code == 200
    assert resp.json() == {
        "total_issues": 3,
        "done_issues": 1,
        "active_issues": 2,
        "issue_progress_percent": 33,
        "point_progress_percent": 50,
        "blocked_count": 1,
        "overdue_count": 1,
        "at_risk_count": 2,
    }
