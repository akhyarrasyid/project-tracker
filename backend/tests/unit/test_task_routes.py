import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from tests.conftest import seed_test_hierarchy


@pytest.fixture
def task_client(db_session):
    seed_test_hierarchy(db_session)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_tasks_worker_not_in_any_project(task_client, db_session):
    seed = seed_test_hierarchy(db_session)
    # Create worker with no project memberships
    worker_no_member = User(
        email="nomember@tracker.com",
        username="nomember",
        full_name="No Member User",
        hashed_password="hashedpassword",
        role="worker",
        team_id=seed["team_id"],
        is_active=True,
    )
    db_session.add(worker_no_member)
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: worker_no_member

    resp = task_client.get("/api/v1/tasks/")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_list_tasks_worker_unauthorized_project_filter(task_client, db_session):
    seed = seed_test_hierarchy(db_session)

    app.dependency_overrides[get_current_user] = lambda: seed["worker"]

    # Filter by non-existent or unauthorized project_id
    resp = task_client.get("/api/v1/tasks/?project_id=99999")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "You do not have access to this project"
