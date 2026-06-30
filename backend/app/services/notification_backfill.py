"""One-off backfill utilities for legacy notification status labels."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Iterable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models.notification import Notification
from app.db.session import SessionLocal

LEGACY_STATUS_LABELS = {
    "TaskStatus.TODO": "Todo",
    "TaskStatus.IN_PROGRESS": "In Progress",
    "TaskStatus.REVIEW": "Review",
    "TaskStatus.DONE": "Done",
}


@dataclass
class NotificationBackfillReport:
    scanned_rows: int
    matched_rows: int
    updated_rows: int
    affected_patterns: dict[str, int]
    dry_run: bool


def _replace_legacy_status_tokens(value: str | None) -> tuple[str | None, Counter[str]]:
    if value is None:
        return None, Counter()

    updated = value
    counts: Counter[str] = Counter()
    for legacy, canonical in LEGACY_STATUS_LABELS.items():
        occurrences = updated.count(legacy)
        if occurrences:
            updated = updated.replace(legacy, canonical)
            counts[legacy] += occurrences
    return updated, counts


def _matching_notifications(db: Session) -> Iterable[Notification]:
    return (
        db.query(Notification)
        .filter(
            or_(
                Notification.title.contains("TaskStatus."),
                Notification.body_preview.contains("TaskStatus."),
            )
        )
        .order_by(Notification.id.asc())
        .all()
    )


def backfill_legacy_notification_status_labels(
    db: Session,
    *,
    dry_run: bool,
) -> NotificationBackfillReport:
    savepoint = db.begin_nested() if dry_run else None
    rows = list(_matching_notifications(db))
    affected_patterns: Counter[str] = Counter()
    updated_rows = 0

    for notification in rows:
        updated_title, title_counts = _replace_legacy_status_tokens(notification.title)
        updated_body, body_counts = _replace_legacy_status_tokens(notification.body_preview)
        combined_counts = title_counts + body_counts

        if not combined_counts:
            continue

        affected_patterns.update(combined_counts)
        updated_rows += 1
        if dry_run:
            continue

        notification.title = updated_title or notification.title
        notification.body_preview = updated_body

    if dry_run:
        assert savepoint is not None
        savepoint.rollback()
    elif updated_rows:
        db.commit()

    return NotificationBackfillReport(
        scanned_rows=len(rows),
        matched_rows=len(rows),
        updated_rows=0 if dry_run else updated_rows,
        affected_patterns=dict(sorted(affected_patterns.items())),
        dry_run=dry_run,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill legacy TaskStatus.* labels in notification titles and previews.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report affected rows without writing changes.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = backfill_legacy_notification_status_labels(db, dry_run=args.dry_run)
    finally:
        db.close()

    print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    main()
