import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

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
    report_path = Path("backend/.runtime/seed-service-test-report.json")
    if report_path.exists():
        report_path.unlink()

    with pytest.raises(SystemExit) as excinfo:
        seed_service.cmd_dry_run("smoke", report_path=str(report_path))

    assert excinfo.value.code == 0
    assert report_path.exists()
    assert "smoke" in report_path.read_text(encoding="utf-8")
    report_path.unlink()
