"""Add optimistic versioning and parent issue references.

Revision ID: 006_issue_version_parent
Revises: 005_task_rank
Create Date: 2026-06-30 01:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "006_issue_version_parent"
down_revision: Union[str, None] = "005_task_rank"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE tasks
            ADD COLUMN IF NOT EXISTS version INTEGER
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tasks
            SET version = 1
            WHERE version IS NULL OR version < 1
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE tasks
            ALTER COLUMN version SET NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE tasks
            ALTER COLUMN version SET DEFAULT 1
            """
        )
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE tasks
            ADD COLUMN IF NOT EXISTS parent_id INTEGER
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
                    WHERE conname = 'fk_tasks_parent_id_tasks'
                ) THEN
                    ALTER TABLE tasks
                    ADD CONSTRAINT fk_tasks_parent_id_tasks
                    FOREIGN KEY (parent_id) REFERENCES tasks(id) ON DELETE SET NULL;
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
                    WHERE conname = 'ck_tasks_parent_not_self'
                ) THEN
                    ALTER TABLE tasks
                    ADD CONSTRAINT ck_tasks_parent_not_self
                    CHECK (parent_id IS NULL OR parent_id <> id);
                END IF;
            END
            $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_tasks_parent_id
            ON tasks (parent_id)
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_tasks_parent_id"))
    op.execute(
        sa.text(
            """
            ALTER TABLE tasks
            DROP CONSTRAINT IF EXISTS ck_tasks_parent_not_self
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE tasks
            DROP CONSTRAINT IF EXISTS fk_tasks_parent_id_tasks
            """
        )
    )
    op.execute(sa.text("ALTER TABLE tasks DROP COLUMN IF EXISTS parent_id"))
    op.execute(sa.text("ALTER TABLE tasks DROP COLUMN IF EXISTS version"))
