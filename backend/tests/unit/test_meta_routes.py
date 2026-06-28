import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.db.models.project import Project
from app.db.session import get_db
from app.main import app
from tests.conftest import seed_test_hierarchy


@pytest.fixture
def meta_client(db_session):
    seed_test_hierarchy(db_session)

    # We want to dynamically configure the logged in user roles/access.
    # We will override get_current_user in individual tests if needed, or default to worker/admin.
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_get_departments(meta_client, db_session):
    # Set default admin user for route
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    resp = meta_client.get("/api/v1/meta/departments")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert resp.json()[0]["name"] == "Engineering"


def test_get_teams_no_filter(meta_client, db_session):
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    resp = meta_client.get("/api/v1/meta/teams")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert resp.json()[0]["name"] == "Backend Team"


def test_get_teams_with_filter(meta_client, db_session):
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    resp = meta_client.get(f"/api/v1/meta/teams?department_id={seed['dept_id']}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp_empty = meta_client.get("/api/v1/meta/teams?department_id=9999")
    assert resp_empty.status_code == 200
    assert len(resp_empty.json()) == 0


def test_get_projects_admin(meta_client, db_session):
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    resp = meta_client.get("/api/v1/meta/projects")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_projects_worker_restricted(meta_client, db_session):
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["worker"]

    # The seed worker is member of seed project
    resp = meta_client.get("/api/v1/meta/projects")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert resp.json()[0]["id"] == seed["project_id"]

    # Now create another project that user is NOT member of
    other_proj = Project(
        name="Untracked Project",
        key="UNT",
        description="Untracked",
        team_id=seed["team_id"],
        status="ACTIVE",
    )
    db_session.add(other_proj)
    db_session.commit()

    resp_after = meta_client.get("/api/v1/meta/projects")
    assert resp_after.status_code == 200
    # Should still only see their own project
    assert len(resp_after.json()) == 1


def test_get_projects_filtered_by_team(meta_client, db_session):
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    resp = meta_client.get(f"/api/v1/meta/projects?team_id={seed['team_id']}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp_empty = meta_client.get("/api/v1/meta/projects?team_id=9999")
    assert resp_empty.status_code == 200
    assert len(resp_empty.json()) == 0


def test_get_users_no_filter(meta_client, db_session):
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    resp = meta_client.get("/api/v1/meta/users")
    assert resp.status_code == 200
    # Should see admin and worker
    assert len(resp.json()) >= 2


def test_get_users_filtered_by_project(meta_client, db_session):
    seed = seed_test_hierarchy(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    resp = meta_client.get(f"/api/v1/meta/users?project_id={seed['project_id']}")
    assert resp.status_code == 200
    # Both are members of project
    assert len(resp.json()) >= 2
