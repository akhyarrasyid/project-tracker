import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db
from app.core.security import get_current_user
from app.db.models.user import User
from app.db.models.team import Team
from app.db.models.department import Department
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from tests.conftest import seed_test_hierarchy

@pytest.fixture
def import_client(db_session):
    seed = seed_test_hierarchy(db_session)
    
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c, seed
    app.dependency_overrides.clear()


def test_download_import_template(import_client):
    client, seed = import_client
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]
    
    resp = client.get("/api/v1/tasks/import-template")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "project_id,project_key,title" in resp.text


def test_import_csv_success_admin(import_client, db_session):
    client, seed = import_client
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    csv_data = (
        "project_id,project_key,title,description,status,priority,due_date,story_points,estimated_hours,assignee_email,tags\n"
        f",PRJ,Test CSV Task 1,This is description,Todo,Medium,2026-07-20,3,8,,backend,api\n"
    )

    files = {"file": ("tasks.csv", csv_data, "text/csv")}
    resp = client.post("/api/v1/tasks/import-csv", files=files)
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert "Berhasil mengimpor 1 task" in resp.json()["message"]


def test_import_csv_validation_errors(import_client, db_session):
    client, seed = import_client
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    csv_data = (
        "project_id,project_key,title,description,status,priority,due_date,story_points,estimated_hours,assignee_email,tags\n"
        f",PRJ,,This is description,Todo,Medium,2026-07-20,3,8,,backend,api\n"  # Missing title
        f",PRJ,Task 2,Desc,InvalidStatus,Medium,2026-07-20,3,8,,\n"             # Invalid status
        f",PRJ,Task 3,Desc,Todo,Medium,2026-07-20,99,8,,\n"                    # Invalid story points
        f",PRJ,Task 4,Desc,Todo,Medium,invalid-date,3,8,,\n"                  # Invalid date format
    )

    files = {"file": ("tasks.csv", csv_data, "text/csv")}
    resp = client.post("/api/v1/tasks/import-csv", files=files)
    
    assert resp.status_code == 422
    err_detail = resp.json()["detail"]
    assert "errors" in err_detail
    errors = err_detail["errors"]
    assert len(errors) == 4
    
    rows = [e["row"] for e in errors]
    fields = [e["field"] for e in errors]
    assert 2 in rows  # missing title
    assert 3 in rows  # invalid status
    assert 4 in rows  # invalid story points
    assert 5 in rows  # invalid date


def test_import_csv_department_boundary_worker(import_client, db_session):
    client, seed = import_client
    
    # 1. Create a different department and team
    other_dept = Department(name="Finance Department", description="Finance Dept")
    db_session.add(other_dept)
    db_session.flush()

    other_team = Team(name="Accounting Team", department_id=other_dept.id)
    db_session.add(other_team)
    db_session.flush()

    # 2. Create project under the other department's team
    other_project = Project(
        name="Finance Audit Project",
        key="FIN",
        team_id=other_team.id,
        status="ACTIVE"
    )
    db_session.add(other_project)
    db_session.flush()

    # Worker is in the Engineering department (Backend Team)
    app.dependency_overrides[get_current_user] = lambda: seed["worker"]

    # Try importing tasks for the Finance project
    csv_data = (
        "project_id,project_key,title,description,status,priority,due_date,story_points,estimated_hours,assignee_email,tags\n"
        f",FIN,Unauthorized Task,This should fail,Todo,Medium,2026-07-20,3,8,,\n"
    )

    files = {"file": ("tasks.csv", csv_data, "text/csv")}
    resp = client.post("/api/v1/tasks/import-csv", files=files)
    
    assert resp.status_code == 422
    err_detail = resp.json()["detail"]
    assert "errors" in err_detail
    errors = err_detail["errors"]
    assert len(errors) == 1
    assert errors[0]["field"] == "project_key"
    assert "diizinkan" in errors[0]["message"]
    assert "departemen lain" in errors[0]["message"]
