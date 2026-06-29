"""Expand notifications and watcher state for Inbox and watch workflows.

Revision ID: 007_notifications_watchers
Revises: 006_issue_version_parent
Create Date: 2026-06-30 09:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "007_notifications_watchers"
down_revision: Union[str, None] = "006_issue_version_parent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE notifications
            ALTER COLUMN actor_id DROP NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE notifications
            ADD COLUMN IF NOT EXISTS issue_id INTEGER
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE notifications
            ADD COLUMN IF NOT EXISTS project_id INTEGER
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE notifications
            ADD COLUMN IF NOT EXISTS type VARCHAR(50)
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE notifications
            ADD COLUMN IF NOT EXISTS title VARCHAR(255)
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE notifications
            ADD COLUMN IF NOT EXISTS body_preview TEXT
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE notifications
            ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE notifications
            ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE notifications
            ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(255)
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'fk_notifications_issue_id_tasks'
                ) THEN
                    ALTER TABLE notifications
                    ADD CONSTRAINT fk_notifications_issue_id_tasks
                    FOREIGN KEY (issue_id) REFERENCES tasks(id) ON DELETE CASCADE;
                END IF;
            END
            $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'fk_notifications_project_id_projects'
                ) THEN
                    ALTER TABLE notifications
                    ADD CONSTRAINT fk_notifications_project_id_projects
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
                END IF;
            END
            $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE notifications
            SET
                issue_id = CASE
                    WHEN entity_type = 'task' THEN entity_id
                    ELSE issue_id
                END,
                type = COALESCE(type, 'legacy_event'),
                title = COALESCE(title, action),
                metadata = CASE
                    WHEN metadata IS NULL OR metadata = '{}'::jsonb THEN
                        jsonb_build_object(
                            'legacy_action', action,
                            'entity_type', entity_type,
                            'entity_id', entity_id
                        )
                    ELSE metadata
                END
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE notifications AS notifications
            SET project_id = tasks.project_id
            FROM tasks
            WHERE notifications.issue_id = tasks.id
              AND notifications.project_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE notifications
            SET read_at = created_at
            WHERE is_read = TRUE
              AND read_at IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_notifications_recipient_created
            ON notifications (recipient_id, created_at DESC, id DESC)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_notifications_recipient_unread
            ON notifications (recipient_id, is_read, created_at DESC, id DESC)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_notifications_dedupe_key
            ON notifications (dedupe_key)
            WHERE dedupe_key IS NOT NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE watchers
            ADD COLUMN IF NOT EXISTS added_by_id INTEGER
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE watchers
            ADD COLUMN IF NOT EXISTS is_watching BOOLEAN NOT NULL DEFAULT TRUE
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE watchers
            ADD COLUMN IF NOT EXISTS unwatched_at TIMESTAMPTZ
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'fk_watchers_added_by_id_users'
                ) THEN
                    ALTER TABLE watchers
                    ADD CONSTRAINT fk_watchers_added_by_id_users
                    FOREIGN KEY (added_by_id) REFERENCES users(id) ON DELETE SET NULL;
                END IF;
            END
            $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE watchers
            SET is_watching = TRUE,
                unwatched_at = NULL
            WHERE is_watching IS DISTINCT FROM TRUE
               OR unwatched_at IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_watchers_task_active
            ON watchers (task_id, is_watching, created_at, user_id)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_watchers_user_active
            ON watchers (user_id, is_watching, created_at, task_id)
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tasks AS tasks
            SET watchers_count = watcher_totals.total_count
            FROM (
                SELECT task_id, COUNT(*)::INTEGER AS total_count
                FROM watchers
                WHERE is_watching = TRUE
                GROUP BY task_id
            ) AS watcher_totals
            WHERE tasks.id = watcher_totals.task_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tasks
            SET watchers_count = 0
            WHERE id NOT IN (
                SELECT DISTINCT task_id
                FROM watchers
                WHERE is_watching = TRUE
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_watchers_user_active"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_watchers_task_active"))
    op.execute(
        sa.text(
            """
            ALTER TABLE watchers
            DROP CONSTRAINT IF EXISTS fk_watchers_added_by_id_users
            """
        )
    )
    op.execute(sa.text("ALTER TABLE watchers DROP COLUMN IF EXISTS unwatched_at"))
    op.execute(sa.text("ALTER TABLE watchers DROP COLUMN IF EXISTS is_watching"))
    op.execute(sa.text("ALTER TABLE watchers DROP COLUMN IF EXISTS added_by_id"))

    op.execute(sa.text("DROP INDEX IF EXISTS uq_notifications_dedupe_key"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_notifications_recipient_unread"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_notifications_recipient_created"))
    op.execute(
        sa.text(
            """
            ALTER TABLE notifications
            DROP CONSTRAINT IF EXISTS fk_notifications_project_id_projects
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE notifications
            DROP CONSTRAINT IF EXISTS fk_notifications_issue_id_tasks
            """
        )
    )
    op.execute(sa.text("ALTER TABLE notifications DROP COLUMN IF EXISTS dedupe_key"))
    op.execute(sa.text("ALTER TABLE notifications DROP COLUMN IF EXISTS read_at"))
    op.execute(sa.text('ALTER TABLE notifications DROP COLUMN IF EXISTS "metadata"'))
    op.execute(sa.text("ALTER TABLE notifications DROP COLUMN IF EXISTS body_preview"))
    op.execute(sa.text("ALTER TABLE notifications DROP COLUMN IF EXISTS title"))
    op.execute(sa.text("ALTER TABLE notifications DROP COLUMN IF EXISTS type"))
    op.execute(sa.text("ALTER TABLE notifications DROP COLUMN IF EXISTS project_id"))
    op.execute(sa.text("ALTER TABLE notifications DROP COLUMN IF EXISTS issue_id"))
    op.execute(
        sa.text(
            """
            ALTER TABLE notifications
            ALTER COLUMN actor_id SET NOT NULL
            """
        )
    )
