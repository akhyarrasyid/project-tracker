from datetime import UTC, datetime

from app.db.models.notification import Notification
from app.services.notification_backfill import (
    backfill_legacy_notification_status_labels,
)
from tests.conftest import seed_test_hierarchy


def test_notification_backfill_is_idempotent_and_updates_only_legacy_status_tokens(
    db_session,
):
    seed = seed_test_hierarchy(db_session)
    legacy = Notification(
        recipient_id=seed["worker"].id,
        actor_id=seed["admin"].id,
        action="status_changed",
        entity_type="task",
        entity_id=1,
        issue_id=None,
        project_id=seed["project_id"],
        type="issue_status_changed",
        title="PAY-86 moved from Todo to TaskStatus.REVIEW",
        body_preview="TaskStatus.IN_PROGRESS follow-up",
        metadata_json={"route_target": "/issues/PAY-86"},
        dedupe_key="legacy-status-title",
        is_read=False,
        created_at=datetime.now(UTC),
    )
    untouched = Notification(
        recipient_id=seed["worker"].id,
        actor_id=seed["admin"].id,
        action="status_changed",
        entity_type="task",
        entity_id=2,
        issue_id=None,
        project_id=seed["project_id"],
        type="issue_status_changed",
        title="PAY-87 moved from Review to In Progress",
        body_preview="Already normalized",
        metadata_json={"route_target": "/issues/PAY-87"},
        dedupe_key="normalized-status-title",
        is_read=False,
        created_at=datetime.now(UTC),
    )
    db_session.add_all([legacy, untouched])
    db_session.commit()

    dry_run_report = backfill_legacy_notification_status_labels(db_session, dry_run=True)
    assert dry_run_report.scanned_rows == 1
    assert dry_run_report.matched_rows == 1
    assert dry_run_report.updated_rows == 0
    assert dry_run_report.affected_patterns == {
        "TaskStatus.IN_PROGRESS": 1,
        "TaskStatus.REVIEW": 1,
    }

    db_session.refresh(legacy)
    assert legacy.title == "PAY-86 moved from Todo to TaskStatus.REVIEW"
    assert legacy.body_preview == "TaskStatus.IN_PROGRESS follow-up"

    apply_report = backfill_legacy_notification_status_labels(db_session, dry_run=False)
    assert apply_report.scanned_rows == 1
    assert apply_report.matched_rows == 1
    assert apply_report.updated_rows == 1

    db_session.refresh(legacy)
    db_session.refresh(untouched)
    assert legacy.title == "PAY-86 moved from Todo to Review"
    assert legacy.body_preview == "In Progress follow-up"
    assert untouched.title == "PAY-87 moved from Review to In Progress"

    second_run_report = backfill_legacy_notification_status_labels(db_session, dry_run=False)
    assert second_run_report.scanned_rows == 0
    assert second_run_report.matched_rows == 0
    assert second_run_report.updated_rows == 0
    assert second_run_report.affected_patterns == {}
