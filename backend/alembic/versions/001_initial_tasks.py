"""Initial schema for project tracker tasks."""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001_initial_tasks"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("team", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(length=50), nullable=True),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="Todo"
        ),
        sa.Column("assignee", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("story_points", sa.Integer(), nullable=True),
        sa.Column("estimated_hours", sa.Integer(), nullable=True),
        sa.Column("actual_hours", sa.Integer(), nullable=True),
        sa.Column(
            "progress_percentage", sa.Integer(), nullable=True, server_default="0"
        ),
        sa.Column("attachments_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("comments_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("watchers_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("sprint", sa.String(length=50), nullable=True),
        sa.Column("quarter", sa.String(length=10), nullable=True),
        sa.Column("risk_level", sa.String(length=50), nullable=True),
        sa.Column("customer_impact", sa.String(length=50), nullable=True),
        sa.Column("sla_hours", sa.Integer(), nullable=True),
        sa.Column(
            "dependencies", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_id"), "tasks", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tasks_id"), table_name="tasks")
    op.drop_table("tasks")
