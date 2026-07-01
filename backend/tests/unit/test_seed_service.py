import argparse
from unittest.mock import patch

import pytest

from app.core.security import verify_password
from app.db.models.activity_log import ActivityLog
from app.db.models.attachment import Attachment
from app.db.models.comment import Comment
from app.db.models.department import Department
from app.db.models.epic import Epic
from app.db.models.notification import Notification
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.models.sprint import Sprint
from app.db.models.task import Task
from app.db.models.team import Team
from app.db.models.user import User
from app.db.models.watcher import Watcher
from app.services import seed_service


@pytest.fixture(autouse=True)
def mock_session_local(monkeypatch, db_session):
    class MockSessionLocal:
        def __init__(self):
            pass

        def __getattr__(self, name):
            if name == "close":
                return lambda: db_session.expunge_all()
            return getattr(db_session, name)

    monkeypatch.setattr("app.services.seed_service.SessionLocal", MockSessionLocal)


def test_load_seed_data_smoke_bundle_contains_catalogs_and_scenarios():
    bundle = seed_service._load_seed_data("smoke")

    assert bundle["profile"]["name"] == "smoke"
    assert bundle["anchor_date"].isoformat() == "2026-06-30"
    assert bundle["random_seed"] == 20260630
    assert len(bundle["scenarios"]) == 4
    assert "organization" in bundle["catalogs"]
    assert "projects" in bundle["catalogs"]


def test_build_profile_dataset_is_deterministic_for_smoke():
    first = seed_service._build_profile_dataset("smoke")
    second = seed_service._build_profile_dataset("smoke")

    assert first["summary"] == second["summary"]
    assert first["tasks"][0]["title"] == second["tasks"][0]["title"]
    assert first["comments"][0]["content"] == second["comments"][0]["content"]


def test_build_profile_dataset_meets_smoke_targets():
    data = seed_service._build_profile_dataset("smoke")
    summary = data["summary"]

    assert summary["projects"] == 4
    assert summary["issues"] >= 40
    assert summary["comments"] >= 60
    assert summary["watchers"] >= 50
    assert summary["notifications"] >= 50
    assert summary["activity_logs"] >= 120
    assert summary["attachments"] >= 18
    assert summary["blocked_issues"] >= 1
    assert summary["sub_issue_links"] >= 1
    assert summary["dependency_links"] >= 10


def test_build_profile_dataset_enterprise_meets_acceptance_basics():
    data = seed_service._build_profile_dataset("enterprise_demo")

    owned_project_teams = {project["team_name"] for project in data["projects"]}
    seeded_teams = {team["name"] for team in data["teams"]}
    assert seeded_teams - owned_project_teams == set()

    membership = {
        (item["project_key"], item["username"]) for item in data["project_members"]
    }
    tasks_by_ref = {task["ref"]: task for task in data["tasks"]}
    invalid_watchers = [
        watcher
        for watcher in data["watchers"]
        if (tasks_by_ref[watcher["task_ref"]]["project_key"], watcher["username"])
        not in membership
    ]
    assert invalid_watchers == []

    project_roles = {}
    for item in data["project_members"]:
        project_roles.setdefault(item["project_key"], set()).add(item["project_role"])
    assert all(
        {"OWNER", "MEMBER", "VIEWER"}.issubset(roles)
        for roles in project_roles.values()
    )

    notification_types = {item["type"] for item in data["notifications"]}
    assert {
        "issue_assigned",
        "issue_mentioned",
        "issue_commented",
        "issue_status_changed",
    }.issubset(notification_types)
    assert all(item["action"] for item in data["notifications"])


def test_cmd_seed_creates_cross_functional_entities(db_session):
    seed_service.cmd_seed("smoke")

    assert db_session.query(Department).count() >= 4
    assert db_session.query(Team).count() >= 7
    assert db_session.query(User).count() >= 15
    assert db_session.query(Project).count() == 4
    assert db_session.query(ProjectMember).count() >= 16
    assert db_session.query(Sprint).count() >= 8
    assert db_session.query(Epic).count() >= 8
    assert db_session.query(Task).count() >= 40
    assert db_session.query(Comment).count() >= 60
    assert db_session.query(Attachment).count() >= 18
    assert db_session.query(Watcher).count() >= 50
    assert db_session.query(Notification).count() >= 50
    assert db_session.query(ActivityLog).count() >= 120

    pay_86 = (
        db_session.query(Task)
        .join(Project, Task.project_id == Project.id)
        .filter(Project.key == "PAY", Task.number == 86)
        .first()
    )
    assert pay_86 is not None
    assert pay_86.comments_count >= 1
    assert pay_86.watchers_count >= 2


def test_cmd_seed_is_idempotent(db_session):
    seed_service.cmd_seed("smoke")
    counts_before = {
        "projects": db_session.query(Project).count(),
        "tasks": db_session.query(Task).count(),
        "comments": db_session.query(Comment).count(),
        "watchers": db_session.query(Watcher).count(),
        "notifications": db_session.query(Notification).count(),
        "activity_logs": db_session.query(ActivityLog).count(),
    }

    seed_service.cmd_seed("smoke")

    counts_after = {
        "projects": db_session.query(Project).count(),
        "tasks": db_session.query(Task).count(),
        "comments": db_session.query(Comment).count(),
        "watchers": db_session.query(Watcher).count(),
        "notifications": db_session.query(Notification).count(),
        "activity_logs": db_session.query(ActivityLog).count(),
    }
    assert counts_after == counts_before


def test_cmd_reset_profile_removes_seeded_projects(db_session):
    seed_service.cmd_seed("smoke")
    assert db_session.query(Project).filter(Project.key.in_(["PAY", "IAM", "PRV", "SUP"])).count() == 4

    seed_service.cmd_reset_profile("smoke")

    assert db_session.query(Project).filter(Project.key.in_(["PAY", "IAM", "PRV", "SUP"])).count() == 0
    assert db_session.query(Task).count() == 0
    assert db_session.query(Comment).count() == 0
    assert db_session.query(Watcher).count() == 0


def test_remote_seed_guard_blocks_without_opt_in(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example.com:5432/app")
    monkeypatch.delenv("ALLOW_REMOTE_SEED", raising=False)
    monkeypatch.delenv("SEED_CONFIRM_PROFILE", raising=False)

    with pytest.raises(SystemExit) as excinfo:
        seed_service._ensure_seed_allowed("enterprise_demo")

    assert excinfo.value.code == 1


def test_main_validate_dispatches_with_profile_argument():
    with patch("argparse.ArgumentParser.parse_args") as mock_parse, patch(
        "app.services.seed_service.cmd_validate"
    ) as mock_cmd_validate:
        mock_parse.return_value = argparse.Namespace(
            seed=False,
            reset_profile=False,
            dry_run=False,
            validate=True,
            profile="smoke",
            anchor_date="2026-06-30",
            random_seed=None,
            report=None,
        )
        seed_service.main()

    mock_cmd_validate.assert_called_once()
    assert mock_cmd_validate.call_args.args[0] == "smoke"


def test_cmd_dry_run_writes_summary_report():
    report_path = seed_service.REPORT_OUTPUT_DIR / "seed-service-test-report.json"
    destination = seed_service.ReportDestination(report_path)
    if report_path.exists():
        report_path.unlink()

    with pytest.raises(SystemExit) as excinfo:
        seed_service.cmd_dry_run("smoke", report_path=destination)

    assert excinfo.value.code == 0
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert '"mode": "dry-run"' in report_text
    assert '"issues"' in report_text
    assert "smoke" not in report_text
    report_path.unlink()

def test_build_report_destination_keeps_relative_paths_inside_repo():
    destination = seed_service._build_report_destination(
        seed_service.ReportDestination(
            seed_service._validated_report_path("seed-report.json")
        )
    )

    assert destination is not None
    assert destination == (
        seed_service.REPORT_OUTPUT_DIR / "seed-report.json"
    ).resolve()


def test_parse_report_path_returns_sanitized_filename():
    destination = seed_service._parse_report_path(".runtime/seed-report.json")

    assert destination.path == (seed_service.REPORT_OUTPUT_DIR / "seed-report.json").resolve()


def test_write_runtime_report_keeps_file_inside_runtime_directory():
    report_path = seed_service.REPORT_OUTPUT_DIR / "validated-report.json"
    destination = seed_service.ReportDestination(report_path)
    if report_path.exists():
        report_path.unlink()

    seed_service._write_runtime_report(destination, {"mode": "test"})

    assert report_path.exists()
    assert '"mode": "test"' in report_path.read_text(encoding="utf-8")
    report_path.unlink()


def test_build_report_destination_rejects_parent_escape():
    with pytest.raises(ValueError):
        seed_service._build_report_destination(
            seed_service.ReportDestination(seed_service.REPO_ROOT / "outside-report.json")
        )


def test_parse_report_path_rejects_parent_escape():
    with pytest.raises(argparse.ArgumentTypeError):
        seed_service._parse_report_path("../../outside-report.json")


def test_parse_report_path_rejects_absolute_paths():
    with pytest.raises(argparse.ArgumentTypeError):
        seed_service._parse_report_path("C:/tmp/report.json")


def test_parse_report_path_rejects_nested_directories():
    with pytest.raises(argparse.ArgumentTypeError):
        seed_service._parse_report_path("reports/nested/report.json")


def test_release_demo_reseed_rotates_demo_passwords_only(monkeypatch, db_session):
    monkeypatch.setenv("DEMO_SEED_PASSWORD", "first-demo-password")
    seed_service.cmd_seed("release_demo")

    tracked_usernames = {
        "admin",
        "payment_owner",
        "engineering_member",
        "legal_member",
        "viewer_user",
    }
    demo_hashes_before = {
        user.username: user.hashed_password
        for user in db_session.query(User)
        .filter(User.username.in_(tracked_usernames))
        .all()
    }
    non_demo_user = (
        db_session.query(User)
        .filter(~User.username.in_(tracked_usernames))
        .order_by(User.username.asc())
        .first()
    )
    assert non_demo_user is not None
    non_demo_user_id = non_demo_user.id
    non_demo_hash_before = non_demo_user.hashed_password

    monkeypatch.setenv("DEMO_SEED_PASSWORD", "second-demo-password")
    seed_service.cmd_seed("release_demo")

    for username in tracked_usernames:
        user = db_session.query(User).filter(User.username == username).one()
        assert user.hashed_password != demo_hashes_before[username]
        assert verify_password("second-demo-password", user.hashed_password)

    unchanged_non_demo = (
        db_session.query(User).filter(User.id == non_demo_user_id).one()
    )
    assert unchanged_non_demo.hashed_password == non_demo_hash_before


def test_release_demo_seed_writes_local_credential_file(monkeypatch):
    credential_path = seed_service.DEMO_ACCOUNTS_LOCAL_FILE
    if credential_path.exists():
        credential_path.unlink()

    monkeypatch.chdir(seed_service.REPO_ROOT / "backend")
    monkeypatch.setenv("DEMO_SEED_PASSWORD", "local-demo-password")
    monkeypatch.setenv("VITE_API_URL", "https://technical-test-project-tracker-api.vercel.app")
    monkeypatch.setenv("DEMO_FRONTEND_URL", "https://technical-test-project-tracker.vercel.app")

    seed_service.cmd_seed("release_demo")

    assert credential_path.exists()
    contents = credential_path.read_text(encoding="utf-8")
    assert "admin" in contents
    assert "payment_owner" in contents
    assert "engineering_member" in contents
    assert "legal_member" in contents
    assert "viewer_user" in contents
    assert "https://technical-test-project-tracker.vercel.app" in contents
    assert "https://technical-test-project-tracker-api.vercel.app/docs" in contents

    credential_path.unlink()


def test_log_demo_accounts_ready_logs_count_only(caplog):
    caplog.set_level("INFO")
    seed_service._log_demo_accounts_ready(2)

    assert "Demo accounts ready for 2 accounts." in caplog.text
    assert "viewer_user" not in caplog.text
    assert "admin" not in caplog.text
    assert "Credential file" not in caplog.text
