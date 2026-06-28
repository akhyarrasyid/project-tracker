import datetime
from typing import Optional, List
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    ForeignKey,
    func
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base

class Task(Base):
    """Task aggregate root — evolved with normalization and project association."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    sprint_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("sprints.id", ondelete="SET NULL"),
        nullable=True
    )
    epic_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("epics.id", ondelete="SET NULL"),
        nullable=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Todo")
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default="Medium")
    quarter: Mapped[str] = mapped_column(String(5), nullable=False, default="Q1")
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False, default="Low")
    customer_impact: Mapped[str] = mapped_column(String(20), nullable=False, default="None")

    assignee_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    created_by_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    due_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    story_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    estimated_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    actual_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_percentage: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    attachments_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    comments_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    watchers_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=48)

    dependencies: Mapped[List[int]] = mapped_column(JSON, nullable=False, default=list)
    tags: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)

    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    deleted_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

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
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_priority", "priority"),
        Index("ix_tasks_due_date", "due_date"),
        Index("ix_tasks_created_at", "created_at"),
    )
