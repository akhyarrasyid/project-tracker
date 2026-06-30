"""Add board rank to tasks.

Revision ID: 005_task_rank
Revises: 004_blocked_flag
Create Date: 2026-06-29 23:40:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "005_task_rank"
down_revision: Union[str, None] = "004_blocked_flag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RANK_STEP = 1024


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE tasks
            ADD COLUMN IF NOT EXISTS rank BIGINT
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            WITH ordered AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY project_id, status
                        ORDER BY created_at, id
                    ) * {RANK_STEP} AS new_rank
                FROM tasks
                WHERE deleted_at IS NULL
            )
            UPDATE tasks
            SET rank = ordered.new_rank
            FROM ordered
            WHERE tasks.id = ordered.id
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            UPDATE tasks
            SET rank = {RANK_STEP}
            WHERE rank IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE tasks
            ALTER COLUMN rank SET NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            ALTER TABLE tasks
            ALTER COLUMN rank SET DEFAULT {RANK_STEP}
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_tasks_project_status_rank
            ON tasks (project_id, status, rank)
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_tasks_project_status_rank"))
    op.execute(sa.text("ALTER TABLE tasks DROP COLUMN IF EXISTS rank"))
