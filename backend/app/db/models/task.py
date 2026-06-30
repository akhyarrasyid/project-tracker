import datetime
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    BigInteger,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

ONDELETE_SET_NULL = "SET NULL"
USERS_ID_FK = "users.id"


class Task(Base):
    """Task aggregate root — evolved with normalization and project association."""

    __tablename__ = "tasks"

    project = relationship("Project", foreign_keys="Task.project_id", lazy="joined")
    sprint_relation = relationship(
        "Sprint", foreign_keys="Task.sprint_id", lazy="joined"
    )
    assignee_relation = relationship(
        "User", foreign_keys="Task.assignee_id", lazy="joined"
    )
    creator = relationship("User", foreign_keys="Task.created_by_id", lazy="joined")
    parent = relationship(
        "Task",
        remote_side="Task.id",
        foreign_keys="Task.parent_id",
        lazy="selectin",
    )

    @property
    def department(self) -> Optional[str]:
        if self.project and self.project.team and self.project.team.department:
            return self.project.team.department.name
        return None

    @property
    def team(self) -> Optional[str]:
        if self.project and self.project.team:
            return self.project.team.name
        return None

    @property
    def assignee(self) -> Optional[str]:
        return self.assignee_relation.full_name if self.assignee_relation else None

    @property
    def created_by(self) -> str:
        return self.creator.username if self.creator else "admin"

    @property
    def sprint(self) -> Optional[str]:
        return self.sprint_relation.name if self.sprint_relation else None

    @property
    def project_key(self) -> Optional[str]:
        return self.project.key if self.project else None

    @property
    def key(self) -> Optional[str]:
        if self.project_key is None or self.number is None:
            return None
        return f"{self.project_key}-{self.number}"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sprint_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sprints.id", ondelete=ONDELETE_SET_NULL), nullable=True
    )
    epic_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("epics.id", ondelete=ONDELETE_SET_NULL), nullable=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1024)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete=ONDELETE_SET_NULL), nullable=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Todo")
    is_blocked: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default="Medium")
    quarter: Mapped[str] = mapped_column(String(5), nullable=False, default="Q1")
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False, default="Low")
    customer_impact: Mapped[str] = mapped_column(
        String(20), nullable=False, default="None"
    )

    assignee_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey(USERS_ID_FK, ondelete=ONDELETE_SET_NULL), nullable=True
    )
    created_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(USERS_ID_FK, ondelete="RESTRICT"), nullable=False
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    due_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey(USERS_ID_FK, ondelete=ONDELETE_SET_NULL), nullable=True
    )

    story_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    estimated_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    actual_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_percentage: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )

    attachments_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    comments_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    watchers_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=48)

    dependencies: Mapped[List[int]] = mapped_column(JSON, nullable=False, default=list)
    tags: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)

    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey(USERS_ID_FK, ondelete=ONDELETE_SET_NULL), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('Todo', 'In Progress', 'Review', 'Done')",
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
        Index("ix_tasks_is_blocked", "is_blocked"),
        Index("ix_tasks_due_date", "due_date"),
        Index("ix_tasks_created_at", "created_at"),
        Index("ix_tasks_project_status_rank", "project_id", "status", "rank"),
        Index("ix_tasks_parent_id", "parent_id"),
        CheckConstraint("version >= 1", name="ck_tasks_version_positive"),
        CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name="ck_tasks_parent_not_self",
        ),
    )
