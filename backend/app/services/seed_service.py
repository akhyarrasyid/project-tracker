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
from typing import Any, Dict, List

from pydantic import ValidationError

from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.schemas.task import TaskCreate

# Import models so metadata is populated
import app.db.models  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SEED_FILE = Path(__file__).resolve().parents[2] / "app" / "db" / "seeds" / "project_tracker_seed.json"


def _load_seed_data() -> List[Dict[str, Any]]:
    if not SEED_FILE.exists():
        log.error(f"Seed file not found: {SEED_FILE}")
        sys.exit(1)
    with SEED_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate all records through Pydantic. Returns list of valid data dicts."""
    valid = []
    errors = []
    for i, record in enumerate(records):
        try:
            validated = TaskCreate(**record)
            dump = validated.model_dump()
            if "id" in record:
                dump["id"] = record["id"]
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
        log.error(f"{len(errors)} record(s) failed validation. Fix them before seeding.")
        sys.exit(1)
    log.info("All records are valid. Safe to seed.")
    sys.exit(0)


def cmd_dry_run(records: List[Dict[str, Any]]) -> None:
    log.info(f"Dry-run: validating {len(records)} records (no DB writes) ...")
    valid, errors = _validate_records(records)
    log.info(f"Dry-run complete — {len(valid)} would be inserted, {len(errors)} would be skipped.")
    if errors:
        log.warning(f"{len(errors)} records would be skipped due to validation errors.")
    sys.exit(0)  # dry-run is always informational; never a hard failure


def cmd_seed(records: List[Dict[str, Any]]) -> None:
    from app.db.models.task import Task

    log.info(f"Seeding {len(records)} records ...")
    valid_data, errors = _validate_records(records)
    if not valid_data:
        log.error("No valid records to insert.")
        sys.exit(1)

    db = SessionLocal()
    try:
        # Determine which IDs already exist
        existing_ids = {row[0] for row in db.query(Task.id).all()}
        to_insert = [d for d in valid_data if d.get("id") not in existing_ids]
        skipped = len(valid_data) - len(to_insert)

        if not to_insert:
            log.info("All records already exist — nothing to insert.")
            return

        log.info(f"Inserting {len(to_insert)} records ({skipped} skipped, {len(errors)} invalid) ...")
        tasks = [Task(**d) for d in to_insert]
        db.bulk_save_objects(tasks)
        db.commit()
        log.info(f"✓ Seeding complete — {len(tasks)} records inserted.")
    except Exception as exc:
        db.rollback()
        log.error(f"Seed failed, transaction rolled back: {exc}")
        sys.exit(1)
    finally:
        db.close()


def cmd_reset(records: List[Dict[str, Any]]) -> None:
    from app.db.models.task import Task

    log.info("Resetting database — dropping and re-seeding all tasks ...")
    db = SessionLocal()
    try:
        deleted = db.query(Task).delete()
        db.commit()
        log.info(f"Deleted {deleted} existing records.")
    except Exception as exc:
        db.rollback()
        log.error(f"Reset failed: {exc}")
        db.close()
        sys.exit(1)
    finally:
        db.close()

    cmd_seed(records)


def main() -> None:
    Base.metadata.create_all(bind=engine)

    parser = argparse.ArgumentParser(description="Project Tracker seed service")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--seed", action="store_true", help="Insert records (idempotent)")
    group.add_argument("--reset", action="store_true", help="DROP all data then re-seed")
    group.add_argument("--dry-run", action="store_true", dest="dry_run", help="Validate only, no writes")
    group.add_argument("--validate", action="store_true", help="Validate JSON structure and enums")
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
