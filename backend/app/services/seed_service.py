import argparse
import datetime
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.models.department import Department
from app.db.models.project import Project
from app.db.models.sprint import Sprint
from app.db.models.task import Task
from app.db.models.team import Team
from app.db.models.user import User
from app.db.session import SessionLocal
from app.schemas.task import TaskCreate

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SEED_FILE = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "db"
    / "seeds"
    / "project_tracker_seed.json"
)

DEFAULT_DEPT_NAME = "Engineering"
DEFAULT_TEAM_NAME = "Default Team"
DEFAULT_PROJECT_NAME = "Default Project"


class SeederContext:
    """Helper to load and cache db models to avoid redundant queries during seeding."""

    def __init__(self, db: Session):
        self.db = db
        self.depts_cache = {d.name: d.id for d in db.query(Department).all()}
        self.teams_cache = {t.name: t.id for t in db.query(Team).all()}
        self.projects_cache = {p.name: p.id for p in db.query(Project).all()}
        self.project_issue_sequences = {
            p.id: p.issue_sequence for p in db.query(Project).all()
        }
        self.users_cache = {u.full_name: u.id for u in db.query(User).all()}
        self.users_by_username = {u.username: u.id for u in db.query(User).all()}
        self.sprints_cache = {s.name: s.id for s in db.query(Sprint).all()}

    def get_or_create_dept(self, name: str) -> int:
        if name in self.depts_cache:
            return self.depts_cache[name]
        d = Department(name=name, description=f"{name} Department")
        self.db.add(d)
        self.db.flush()
        self.depts_cache[name] = d.id
        return d.id

    def get_or_create_team(self, name: str, dept_id: int) -> int:
        if name in self.teams_cache:
            return self.teams_cache[name]
        t = Team(name=name, department_id=dept_id, description=f"{name} Team")
        self.db.add(t)
        self.db.flush()
        self.teams_cache[name] = t.id
        return t.id

    def get_or_create_project(
        self, name: str, team_id: int, key_override: str | None = None
    ) -> int:
        if name in self.projects_cache:
            return self.projects_cache[name]
        key = key_override or "".join([c for c in name if c.isupper()])[:5]
        if not key:
            key = name[:3].upper()
        project = Project(name=name, key=key, team_id=team_id, status="ACTIVE")
        self.db.add(project)
        self.db.flush()
        self.projects_cache[name] = project.id
        self.project_issue_sequences[project.id] = project.issue_sequence
        return project.id

    def allocate_issue_number(self, project_id: int) -> int:
        current = self.project_issue_sequences.get(project_id)
        if current is None:
            current = (
                self.db.query(Project.issue_sequence)
                .filter(Project.id == project_id)
                .scalar()
                or 0
            )
        next_number = current + 1
        self.project_issue_sequences[project_id] = next_number
        return next_number

    def get_or_create_user(self, full_name: str, team_id: int) -> int:
        from app.core.security import get_password_hash

        if full_name in self.users_cache:
            return self.users_cache[full_name]
        username = full_name.lower().replace(" ", "_")
        if username in self.users_by_username:
            return self.users_by_username[username]
        u = User(
            email=f"{username}@tracker.com",
            username=username,
            full_name=full_name,
            hashed_password=get_password_hash("password123"),
            role="worker",
            team_id=team_id,
            is_active=True,
        )
        self.db.add(u)
        self.db.flush()
        self.users_cache[full_name] = u.id
        self.users_by_username[username] = u.id
        return u.id

    def get_or_create_sprint(self, project_id: int, name: str) -> int:
        if name in self.sprints_cache:
            return self.sprints_cache[name]
        s = Sprint(
            project_id=project_id,
            name=name,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=14),
            status="UPCOMING",
        )
        self.db.add(s)
        self.db.flush()
        self.sprints_cache[name] = s.id
        return s.id


def _load_seed_data() -> List[Dict[str, Any]]:
    if not SEED_FILE.exists():
        log.error(f"Seed file not found: {SEED_FILE}")
        sys.exit(1)
    with SEED_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_records(
    records: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Validate all records through Pydantic. Returns list of valid data dicts."""
    valid = []
    errors = []
    for i, record in enumerate(records):
        try:
            # We copy record and remove legacy string fields before passing to TaskCreate validation,
            # as TaskCreate does not define them anymore, but we want to validate the rest!
            record_clean = {
                k: v
                for k, v in record.items()
                if k
                not in [
                    "department",
                    "team",
                    "assignee",
                    "created_by",
                    "sprint",
                    "project",
                    "project_key",
                ]
            }
            validated = TaskCreate(**record_clean)
            dump = validated.model_dump()
            if "id" in record:
                dump["id"] = record["id"]
            # Keep the legacy string fields on the output dump so that they can be used for mapping in cmd_seed!
            for f in [
                "department",
                "team",
                "assignee",
                "created_by",
                "sprint",
                "project",
                "project_key",
            ]:
                if f in record:
                    dump[f] = record[f]
            valid.append(dump)
        except ValidationError as exc:
            errors.append({"index": i, "id": record.get("id"), "errors": exc.errors()})

    if errors:
        log.warning(f"{len(errors)} record(s) failed validation:")
        for err in errors[:10]:  # show first 10
            log.warning(f"  Record id={err['id']}: {err['errors']}")
    else:
        log.info(f"All {len(valid)} records passed validation.")

    return valid, errors


def cmd_validate(records: List[Dict[str, Any]]) -> None:
    log.info(f"Validating {len(records)} records from {SEED_FILE} ...")
    valid, errors = _validate_records(records)
    log.info(f"Result — valid: {len(valid)}, invalid: {len(errors)}")
    if errors:
        log.error(
            f"{len(errors)} record(s) failed validation. Fix them before seeding."
        )
        sys.exit(1)
    log.info("All records are valid. Safe to seed.")
    sys.exit(0)


def cmd_dry_run(records: List[Dict[str, Any]]) -> None:
    log.info(f"Dry-run: validating {len(records)} records (no DB writes) ...")
    valid, errors = _validate_records(records)
    log.info(
        f"Dry-run complete — {len(valid)} would be inserted, {len(errors)} would be skipped."
    )
    if errors:
        log.warning(f"{len(errors)} records would be skipped due to validation errors.")
    sys.exit(0)  # dry-run is always informational; never a hard failure


def _get_or_create_default_entities(db: Session) -> Tuple[Project, Team]:
    from app.core.security import get_password_hash

    default_dept = (
        db.query(Department).filter(Department.name == DEFAULT_DEPT_NAME).first()
    )
    if not default_dept:
        default_dept = Department(
            name=DEFAULT_DEPT_NAME, description="Default Engineering Department"
        )
        db.add(default_dept)
        db.flush()

    default_team = db.query(Team).filter(Team.name == DEFAULT_TEAM_NAME).first()
    if not default_team:
        default_team = Team(
            name=DEFAULT_TEAM_NAME,
            department_id=default_dept.id,
            description=DEFAULT_TEAM_NAME,
        )
        db.add(default_team)
        db.flush()

    default_project = (
        db.query(Project).filter(Project.name == DEFAULT_PROJECT_NAME).first()
    )
    if not default_project:
        default_project = Project(
            name=DEFAULT_PROJECT_NAME,
            key="DEF",
            team_id=default_team.id,
            status="ACTIVE",
        )
        db.add(default_project)
        db.flush()

    default_user = db.query(User).filter(User.username == "admin").first()
    if not default_user:
        default_user = User(
            email="admin@tracker.com",
            username="admin",
            full_name="Administrator",
            hashed_password=get_password_hash("password123"),
            role="admin",
            team_id=default_team.id,
            is_active=True,
        )
        db.add(default_user)
        db.flush()

    return default_project, default_team


def _prepare_task_record(
    d: Dict[str, Any], default_project: Project, default_team: Team, ctx: SeederContext
) -> Task:
    # Resolve hierarchy
    dept_str = d.get("department")
    team_str = d.get("team")

    project_name = d.get("project")
    project_key = d.get("project_key")

    if dept_str and team_str:
        dept_id = ctx.get_or_create_dept(dept_str)
        team_id = ctx.get_or_create_team(team_str, dept_id)
        resolved_project_name = project_name or f"{team_str} Project"
        project_id = ctx.get_or_create_project(
            resolved_project_name,
            team_id,
            key_override=project_key,
        )
    else:
        project_id = default_project.id
        team_id = default_team.id

    # Resolve assignee and creator
    assignee_str = d.get("assignee")
    assignee_id = (
        ctx.get_or_create_user(assignee_str, team_id) if assignee_str else None
    )

    creator_str = d.get("created_by") or "admin"
    created_by_id = ctx.get_or_create_user(creator_str, team_id)

    # Resolve sprint
    sprint_str = d.get("sprint")
    sprint_id = (
        ctx.get_or_create_sprint(project_id, sprint_str) if sprint_str else None
    )

    # Build Task DB attributes
    task_kwargs = {
        k: v
        for k, v in d.items()
        if k
        not in [
            "department",
            "team",
            "assignee",
            "created_by",
            "sprint",
            "project",
            "project_key",
        ]
    }

    task_kwargs["project_id"] = project_id
    task_kwargs["assignee_id"] = assignee_id
    task_kwargs["created_by_id"] = created_by_id
    task_kwargs["sprint_id"] = sprint_id

    # Strip any None from list-typed columns
    if "dependencies" not in task_kwargs:
        task_kwargs["dependencies"] = []
    if "tags" not in task_kwargs:
        task_kwargs["tags"] = []

    if task_kwargs.get("status") == "Blocked":
        task_kwargs["status"] = "In Progress"
        task_kwargs["is_blocked"] = True
        task_kwargs.setdefault(
            "blocked_reason", "Migrated from legacy blocked status"
        )

    task_number = task_kwargs.get("number")
    if not isinstance(task_number, int) or task_number < 1:
        task_kwargs["number"] = ctx.allocate_issue_number(project_id)
    else:
        ctx.project_issue_sequences[project_id] = max(
            ctx.project_issue_sequences.get(project_id, 0),
            task_number,
        )

    return Task(**task_kwargs)


def cmd_seed(records: List[Dict[str, Any]]) -> None:
    log.info(f"Seeding {len(records)} records ...")
    valid_data, _ = _validate_records(records)
    if not valid_data:
        log.error("No valid records to insert.")
        sys.exit(1)

    db = SessionLocal()
    try:
        default_project, default_team = _get_or_create_default_entities(db)
        ctx = SeederContext(db)
        existing_ids = {row[0] for row in db.query(Task.id).all()}

        to_insert = []
        for d in valid_data:
            if d.get("id") in existing_ids:
                continue
            to_insert.append(
                _prepare_task_record(d, default_project, default_team, ctx)
            )

        if not to_insert:
            log.info("All records already exist — nothing to insert.")
            return

        log.info(f"Inserting {len(to_insert)} records ...")
        db.add_all(to_insert)
        for project_id, issue_sequence in ctx.project_issue_sequences.items():
            db.query(Project).filter(Project.id == project_id).update(
                {"issue_sequence": issue_sequence}
            )
        db.commit()

        # Reset ID sequences to max ID + 1 to prevent sequence out-of-sync insertion conflicts
        _reset_sequences(db)
        log.info(f"✓ Seeding complete — {len(to_insert)} records inserted.")
    except Exception:
        db.rollback()
        log.exception("Seed failed, transaction rolled back.")
        sys.exit(1)
    finally:
        db.close()


def _reset_sequences(db: Session) -> None:
    from sqlalchemy import text

    tables = ["tasks", "users", "departments", "teams", "projects", "sprints"]
    for t in tables:
        try:
            res = db.execute(text(f"SELECT MAX(id) FROM {t}")).scalar()
            max_id = res if res is not None else 0
            next_val = max_id + 1
            db.execute(text(f"SELECT setval('{t}_id_seq', {next_val}, false)"))
        except Exception as e:
            log.warning(f"Failed to reset sequence for table {t}: {e}")
    db.commit()


def cmd_reset(records: List[Dict[str, Any]]) -> None:
    log.info("Resetting database — dropping and re-seeding all tasks ...")
    db = SessionLocal()
    try:
        # Clear child dependencies first, then parents to respect foreign key constraints
        db.query(Task).delete()
        db.query(Sprint).delete()
        db.query(Project).delete()
        db.query(User).delete()
        db.query(Team).delete()
        db.query(Department).delete()

        db.commit()
        log.info("Deleted existing records.")
    except Exception:
        db.rollback()
        log.exception("Reset failed.")
        db.close()
        sys.exit(1)
    finally:
        db.close()

    cmd_seed(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Project Tracker seed service")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--seed", action="store_true", help="Insert records (idempotent)"
    )
    group.add_argument(
        "--reset", action="store_true", help="DROP all data then re-seed"
    )
    group.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Validate only, no writes",
    )
    group.add_argument(
        "--validate", action="store_true", help="Validate JSON structure and enums"
    )
    args = parser.parse_args()

    records = _load_seed_data()
    log.info(f"Loaded {len(records)} records from seed file.")

    if args.validate:
        cmd_validate(records)
    elif args.dry_run:
        cmd_dry_run(records)
    elif args.seed:
        cmd_seed(records)
    elif args.reset:
        cmd_reset(records)


if __name__ == "__main__":
    main()
