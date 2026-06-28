"""Enterprise-grade seed service.

Usage:
    python -m app.services.seed_service --seed
    python -m app.services.seed_service --reset
    python -m app.services.seed_service --dry-run
    python -m app.services.seed_service --validate
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

# Import models so metadata is populated
import app.db.models  # noqa: F401
from app.db.base import Base
from app.db.session import SessionLocal, engine
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
                if k not in ["department", "team", "assignee", "created_by", "sprint"]
            }
            validated = TaskCreate(**record_clean)
            dump = validated.model_dump()
            if "id" in record:
                dump["id"] = record["id"]
            # Keep the legacy string fields on the output dump so that they can be used for mapping in cmd_seed!
            for f in ["department", "team", "assignee", "created_by", "sprint"]:
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


def cmd_seed(records: List[Dict[str, Any]]) -> None:
    from app.core.security import get_password_hash
    from app.db.models.department import Department
    from app.db.models.project import Project
    from app.db.models.sprint import Sprint
    from app.db.models.task import Task
    from app.db.models.team import Team
    from app.db.models.user import User

    log.info(f"Seeding {len(records)} records ...")
    valid_data, errors = _validate_records(records)
    if not valid_data:
        log.error("No valid records to insert.")
        sys.exit(1)

    db = SessionLocal()
    try:
        # We need a default dept/team/project/user to fall back on
        default_dept = (
            db.query(Department).filter(Department.name == "Engineering").first()
        )
        if not default_dept:
            default_dept = Department(
                name="Engineering", description="Default Engineering Department"
            )
            db.add(default_dept)
            db.flush()

        default_team = db.query(Team).filter(Team.name == "Default Team").first()
        if not default_team:
            default_team = Team(
                name="Default Team",
                department_id=default_dept.id,
                description="Default Team",
            )
            db.add(default_team)
            db.flush()

        default_project = (
            db.query(Project).filter(Project.name == "Default Project").first()
        )
        if not default_project:
            default_project = Project(
                name="Default Project",
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

        # Cache lookups to be super fast
        depts_cache = {d.name: d.id for d in db.query(Department).all()}
        teams_cache = {t.name: t.id for t in db.query(Team).all()}
        projects_cache = {p.name: p.id for p in db.query(Project).all()}
        users_cache = {u.full_name: u.id for u in db.query(User).all()}
        users_by_username = {u.username: u.id for u in db.query(User).all()}
        sprints_cache = {s.name: s.id for s in db.query(Sprint).all()}

        # Cache helper functions to resolve or create on the fly
        def get_or_create_dept(name: str) -> int:
            if name in depts_cache:
                return depts_cache[name]
            d = Department(name=name, description=f"{name} Department")
            db.add(d)
            db.flush()
            depts_cache[name] = d.id
            return d.id

        def get_or_create_team(name: str, dept_id: int) -> int:
            if name in teams_cache:
                return teams_cache[name]
            t = Team(name=name, department_id=dept_id, description=f"{name} Team")
            db.add(t)
            db.flush()
            teams_cache[name] = t.id
            return t.id

        def get_or_create_project(name: str, team_id: int) -> int:
            if name in projects_cache:
                return projects_cache[name]
            key = "".join([c for c in name if c.isupper()])[:5]
            if not key:
                key = name[:3].upper()
            project = Project(name=name, key=key, team_id=team_id, status="ACTIVE")
            db.add(project)
            db.flush()
            projects_cache[name] = project.id
            return project.id

        def get_or_create_user(full_name: str, team_id: int) -> int:
            if full_name in users_cache:
                return users_cache[full_name]
            username = full_name.lower().replace(" ", "_")
            if username in users_by_username:
                return users_by_username[username]
            u = User(
                email=f"{username}@tracker.com",
                username=username,
                full_name=full_name,
                hashed_password=get_password_hash("password123"),
                role="worker",
                team_id=team_id,
                is_active=True,
            )
            db.add(u)
            db.flush()
            users_cache[full_name] = u.id
            users_by_username[username] = u.id
            return u.id

        def get_or_create_sprint(name: str) -> int:
            if name in sprints_cache:
                return sprints_cache[name]
            import datetime

            s = Sprint(
                name=name,
                start_date=datetime.date.today(),
                end_date=datetime.date.today() + datetime.timedelta(days=14),
                status="UPCOMING",
            )
            db.add(s)
            db.flush()
            sprints_cache[name] = s.id
            return s.id

        existing_ids = {row[0] for row in db.query(Task.id).all()}

        # Prepare records for insertion
        to_insert = []
        for d in valid_data:
            if d.get("id") in existing_ids:
                continue

            # Resolve hierarchy
            dept_str = d.get("department")
            team_str = d.get("team")

            if dept_str and team_str:
                dept_id = get_or_create_dept(dept_str)
                team_id = get_or_create_team(team_str, dept_id)
                project_id = get_or_create_project(f"{team_str} Project", team_id)
            else:
                project_id = default_project.id
                team_id = default_team.id

            # Resolve assignee and creator
            assignee_str = d.get("assignee")
            assignee_id = (
                get_or_create_user(assignee_str, team_id) if assignee_str else None
            )

            creator_str = d.get("created_by") or "admin"
            created_by_id = get_or_create_user(creator_str, team_id)

            # Resolve sprint
            sprint_str = d.get("sprint")
            sprint_id = get_or_create_sprint(sprint_str) if sprint_str else None

            # Build Task DB attributes
            # Remove legacy fields
            task_kwargs = {
                k: v
                for k, v in d.items()
                if k not in ["department", "team", "assignee", "created_by", "sprint"]
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

            to_insert.append(Task(**task_kwargs))

        if not to_insert:
            log.info("All records already exist — nothing to insert.")
            return

        log.info(f"Inserting {len(to_insert)} records ...")
        db.add_all(to_insert)
        db.commit()
        log.info(f"✓ Seeding complete — {len(to_insert)} records inserted.")
    except Exception:
        db.rollback()
        log.exception("Seed failed, transaction rolled back.")
        sys.exit(1)
    finally:
        db.close()


def cmd_reset(records: List[Dict[str, Any]]) -> None:
    from app.db.models.department import Department
    from app.db.models.project import Project
    from app.db.models.sprint import Sprint
    from app.db.models.task import Task
    from app.db.models.team import Team
    from app.db.models.user import User

    log.info("Resetting database — dropping and re-seeding all tasks ...")
    db = SessionLocal()
    try:
        # Clear child dependencies first, then parents to respect foreign key constraints
        db.query(Task).delete()
        db.query(Sprint).delete()
        # Delete projects, users, teams, and departments
        # Note: avoid deleting active seeded users like current admin if they are needed,
        # but in seed reset, everything is re-seeded, so deleting is correct.
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
    Base.metadata.create_all(bind=engine)

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
