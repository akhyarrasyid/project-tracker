import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    recipient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, default="legacy_event")
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, default="task")
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=False)
    issue_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="legacy_event")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dedupe_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    recipient = relationship("User", foreign_keys="Notification.recipient_id", lazy="joined")
    actor = relationship("User", foreign_keys="Notification.actor_id", lazy="joined")
    issue = relationship("Task", foreign_keys="Notification.issue_id", lazy="joined")
    project = relationship("Project", foreign_keys="Notification.project_id", lazy="joined")
