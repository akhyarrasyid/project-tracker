import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
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
    assert "project_key,title" in resp.text
    assert "project_id" not in resp.text


def test_import_csv_success_admin(import_client, db_session):
    client, seed = import_client
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    csv_data = (
        "project_key,title,description,status,priority,due_date,story_points,estimated_hours,assignee_email,tags\n"
        f"PRJ,Test CSV Task 1,This is description,Todo,Medium,2026-07-20,3,8,{seed['worker'].email},backend,api\n"
    )

    files = {"file": ("tasks.csv", csv_data, "text/csv")}
    resp = client.post("/api/v1/tasks/import-csv", files=files)
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert "Berhasil mengimpor 1 task" in resp.json()["message"]


def test_import_csv_success_worker(import_client, db_session):
    client, seed = import_client
    # Worker is in Backend Team, which belongs to Engineering department. Project PRJ is also in Backend Team.
    app.dependency_overrides[get_current_user] = lambda: seed["worker"]

    csv_data = (
        "project_key,title,description,status,priority,due_date,story_points,estimated_hours,assignee_email,tags\n"
        f"PRJ,Worker Task,Worker description,In Progress,High,,5,12,,backend\n"
    )

    files = {"file": ("tasks.csv", csv_data, "text/csv")}
    resp = client.post("/api/v1/tasks/import-csv", files=files)
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_import_csv_missing_headers(import_client):
    client, seed = import_client
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    # Missing "title" header
    csv_data = (
        "project_key,description\n"
        "PRJ,Some description\n"
    )

    files = {"file": ("tasks.csv", csv_data, "text/csv")}
    resp = client.post("/api/v1/tasks/import-csv", files=files)
    assert resp.status_code == 400
    assert "Header CSV tidak valid" in resp.json()["detail"]


def test_import_csv_empty_file(import_client):
    client, seed = import_client
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    # Header present, but no rows
    csv_data = "project_key,title,description,status,priority,due_date,story_points,estimated_hours,assignee_email,tags\n"

    files = {"file": ("tasks.csv", csv_data, "text/csv")}
    resp = client.post("/api/v1/tasks/import-csv", files=files)
    assert resp.status_code == 400
    assert "Tidak ada data task yang valid" in resp.json()["detail"]


def test_import_csv_file_read_error(import_client):
    client, seed = import_client
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    # Sending invalid file type or corrupt upload to cause exception
    files = {"file": ("tasks.csv", b'\xff\xff\xff\xff', "text/csv")}
    resp = client.post("/api/v1/tasks/import-csv", files=files)
    assert resp.status_code == 400
    assert "Gagal membaca file" in resp.json()["detail"]


def test_import_csv_validation_errors(import_client, db_session):
    client, seed = import_client
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    csv_data = (
        "project_key,title,description,status,priority,due_date,story_points,estimated_hours,assignee_email,tags\n"
        f"PRJ,,This is description,Todo,Medium,2026-07-20,3,8,,backend,api\n"  # Missing title
        f"PRJ,Task 2,Desc,InvalidStatus,Medium,2026-07-20,3,8,,\n"             # Invalid status
        f"PRJ,Task 3,Desc,Todo,InvalidPriority,2026-07-20,3,8,,\n"            # Invalid priority
        f"PRJ,Task 4,Desc,Todo,Medium,invalid-date,3,8,,\n"                   # Invalid date format
        f"PRJ,Task 5,Desc,Todo,Medium,2026-07-20,99,8,,\n"                    # Invalid story points (value)
        f"PRJ,Task 6,Desc,Todo,Medium,2026-07-20,not-a-number,8,,\n"           # Invalid story points (type)
        f"PRJ,Task 7,Desc,Todo,Medium,2026-07-20,3,0,,\n"                     # Invalid estimated hours (< 1)
        f"PRJ,Task 8,Desc,Todo,Medium,2026-07-20,3,not-a-number,,\n"           # Invalid estimated hours (type)
        f"PRJ,Task 9,Desc,Todo,Medium,2026-07-20,3,8,nonexistent@example.com,\n" # Invalid assignee email
        f"PRJ,Task 10,Desc,Todo,Medium,2026-07-20,3,8,,\"t1,t2,t3,t4,t5\"\n"   # Too many tags (> 4)
        f"INVALID_KEY,Task 11,Desc,Todo,Medium,2026-07-20,3,8,,\n"             # Invalid project key
    )

    files = {"file": ("tasks.csv", csv_data, "text/csv")}
    resp = client.post("/api/v1/tasks/import-csv", files=files)
    
    assert resp.status_code == 422
    err_detail = resp.json()["detail"]
    assert "errors" in err_detail
    errors = err_detail["errors"]
    assert len(errors) == 11
    
    rows = [e["row"] for e in errors]
    fields = [e["field"] for e in errors]
    
    assert 2 in rows  # missing title
    assert 3 in rows  # invalid status
    assert 4 in rows  # invalid priority
    assert 5 in rows  # invalid date
    assert 6 in rows  # invalid story points (value)
    assert 7 in rows  # invalid story points (type)
    assert 8 in rows  # invalid estimated hours (< 1)
    assert 9 in rows  # invalid estimated hours (type)
    assert 10 in rows # invalid assignee email
    assert 11 in rows # too many tags
    assert 12 in rows # invalid project key


def test_import_csv_db_save_error(import_client, db_session):
    client, seed = import_client
    app.dependency_overrides[get_current_user] = lambda: seed["admin"]

    csv_data = (
        "project_key,title,description,status,priority,due_date,story_points,estimated_hours,assignee_email,tags\n"
        f"PRJ,Rollback Task,Desc,Todo,Medium,2026-07-20,3,8,,\n"
    )

    files = {"file": ("tasks.csv", csv_data, "text/csv")}
    
    # Mock TaskService.create_task to raise an exception to test rollback and 500 error code
    from app.services.task_service import TaskService
    with patch.object(TaskService, "create_task", side_effect=Exception("Database error")):
        resp = client.post("/api/v1/tasks/import-csv", files=files)
        assert resp.status_code == 500
        assert "Kesalahan internal saat menyimpan ke database" in resp.json()["detail"]


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
        "project_key,title,description,status,priority,due_date,story_points,estimated_hours,assignee_email,tags\n"
        f"FIN,Unauthorized Task,This should fail,Todo,Medium,2026-07-20,3,8,,\n"
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
