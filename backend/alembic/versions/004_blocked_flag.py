"""Migrate blocked workflow status into flags.

Revision ID: 004_blocked_flag
Revises: 003_issue_identity
Create Date: 2026-06-29 22:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_blocked_flag"
down_revision: Union[str, None] = "003_issue_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CANONICAL_STATUSES = ("Todo", "In Progress", "Review", "Done")


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE tasks
            ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT false NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE tasks
            ADD COLUMN IF NOT EXISTS blocked_reason TEXT
            """
        )
    )

    op.execute(
        sa.text(
            """
            WITH migrated AS (
                SELECT
                    t.id,
                    COALESCE(
                        (
                            SELECT al.old_value
                            FROM activity_logs al
                            WHERE al.task_id = t.id
                              AND al.field = 'status'
                              AND al.new_value = 'Blocked'
                              AND al.old_value IN ('Todo', 'In Progress', 'Review', 'Done')
                            ORDER BY al.created_at DESC, al.id DESC
                            LIMIT 1
                        ),
                        'In Progress'
                    ) AS restored_status
                FROM tasks t
                WHERE t.status = 'Blocked'
            )
            UPDATE tasks t
            SET
                status = migrated.restored_status,
                is_blocked = true,
                blocked_reason = COALESCE(
                    t.blocked_reason,
                    'Migrated from legacy blocked status'
                )
            FROM migrated
            WHERE t.id = migrated.id
            """
        )
    )

    op.execute(sa.text("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS ck_tasks_status"))
    op.execute(
        sa.text(
            """
            ALTER TABLE tasks
            ADD CONSTRAINT ck_tasks_status
            CHECK (status IN ('Todo', 'In Progress', 'Review', 'Done'))
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_tasks_is_blocked
            ON tasks (is_blocked)
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE tasks
            SET status = 'Blocked'
            WHERE is_blocked = true
            """
        )
    )

    op.execute(sa.text("DROP INDEX IF EXISTS ix_tasks_is_blocked"))
    op.execute(sa.text("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS ck_tasks_status"))
    op.execute(
        sa.text(
            """
            ALTER TABLE tasks
            ADD CONSTRAINT ck_tasks_status
            CHECK (status IN ('Todo', 'In Progress', 'Review', 'Done', 'Blocked'))
            """
        )
    )

    op.execute(sa.text("ALTER TABLE tasks DROP COLUMN IF EXISTS blocked_reason"))
    op.execute(sa.text("ALTER TABLE tasks DROP COLUMN IF EXISTS is_blocked"))
