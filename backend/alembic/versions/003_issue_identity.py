"""Add project-scoped issue identity fields.

Revision ID: 003_issue_identity
Revises: 002_core_hierarchy
Create Date: 2026-06-29 18:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_issue_identity"
down_revision: Union[str, None] = "002_core_hierarchy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column("issue_sequence", sa.Integer(), nullable=False, server_default="0")
        )

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(
            sa.Column("number", sa.Integer(), nullable=True, server_default="0")
        )

    op.execute(
        sa.text(
            """
            WITH numbered_tasks AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY id) AS issue_number
                FROM tasks
                WHERE deleted_at IS NULL
            )
            UPDATE tasks
            SET number = numbered_tasks.issue_number
            FROM numbered_tasks
            WHERE tasks.id = numbered_tasks.id
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE projects
            SET issue_sequence = COALESCE(project_numbers.max_number, 0)
            FROM (
                SELECT project_id, MAX(number) AS max_number
                FROM tasks
                GROUP BY project_id
            ) AS project_numbers
            WHERE projects.id = project_numbers.project_id
            """
        )
    )

    op.execute(sa.text("UPDATE tasks SET number = 0 WHERE number IS NULL"))

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column("number", nullable=False, existing_type=sa.Integer())
        batch_op.create_unique_constraint(
            "uq_tasks_project_number", ["project_id", "number"]
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint("uq_tasks_project_number", type_="unique")
        batch_op.drop_column("number")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("issue_sequence")
