import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.types import JSON

from app.db.base import Base


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class Task(Base):
    """Task aggregate root — mirrors all 26 fields from project_tracker_seed.json."""

    __tablename__ = "tasks"

    # ── Primary key ──────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # ── Core fields ──────────────────────────────────────────────────────
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, server_default="")

    # ── Enum-like string fields (validated at schema layer) ───────────────
    status = Column(String(20), nullable=False, default="Todo")
    priority = Column(String(20), nullable=False, default="Medium")
    quarter = Column(String(5), nullable=False, default="Q1")
    risk_level = Column(String(10), nullable=False, default="Low")
    customer_impact = Column(String(20), nullable=False, default="None")

    # ── Organisation fields ───────────────────────────────────────────────
    department = Column(String(100), nullable=False, default="")
    team = Column(String(100), nullable=False, default="")
    assignee = Column(String(100), nullable=False, default="")
    created_by = Column(String(50), nullable=False, default="")

    # ── Timestamps ───────────────────────────────────────────────────────
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )
    due_date = Column(Date, nullable=False, default=datetime.date.today)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # ── Metrics ──────────────────────────────────────────────────────────
    story_points = Column(SmallInteger, nullable=False, default=1)
    estimated_hours = Column(Integer, nullable=False, default=8)
    actual_hours = Column(Integer, nullable=False, default=0)
    progress_percentage = Column(SmallInteger, nullable=False, default=0)

    # ── Counters ─────────────────────────────────────────────────────────
    attachments_count = Column(SmallInteger, nullable=False, default=0)
    comments_count = Column(SmallInteger, nullable=False, default=0)
    watchers_count = Column(SmallInteger, nullable=False, default=0)

    # ── Sprint / planning ─────────────────────────────────────────────────
    sprint = Column(String(20), nullable=False, default="")

    # ── SLA ──────────────────────────────────────────────────────────────
    sla_hours = Column(Integer, nullable=False, default=48)

    # ── JSON arrays — use `JSON` so SQLite tests work, JSONB in production
    dependencies = Column(JSON, nullable=False, default=list)
    tags = Column(JSON, nullable=False, default=list)

    # ── Table-level CHECK constraints ─────────────────────────────────────
    __table_args__ = (
        CheckConstraint(
            "status IN ('Todo', 'In Progress', 'Review', 'Blocked', 'Done')",
            name="ck_tasks_status",
        ),
        CheckConstraint(
            "priority IN ('Low', 'Medium', 'High', 'Critical')",
            name="ck_tasks_priority",
        ),
        CheckConstraint(
            "quarter IN ('Q1', 'Q2', 'Q3', 'Q4')",
            name="ck_tasks_quarter",
        ),
        CheckConstraint(
            "risk_level IN ('Low', 'Medium', 'High')",
            name="ck_tasks_risk_level",
        ),
        CheckConstraint(
            "customer_impact IN ('None', 'Low', 'Medium', 'High', 'Internal')",
            name="ck_tasks_customer_impact",
        ),
        CheckConstraint(
            "progress_percentage >= 0 AND progress_percentage <= 100",
            name="ck_tasks_progress_percentage",
        ),
        CheckConstraint(
            "story_points IN (1, 2, 3, 5, 8, 13)",
            name="ck_tasks_story_points",
        ),
        # ── Secondary indexes ────────────────────────────────────────────
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_priority", "priority"),
        Index("ix_tasks_department", "department"),
        Index("ix_tasks_assignee", "assignee"),
        Index("ix_tasks_due_date", "due_date"),
        Index("ix_tasks_sprint", "sprint"),
        Index("ix_tasks_created_at", "created_at"),
    )
