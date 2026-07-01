from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import (
    CreatedUpdatedServerTimestampsMixin,
    SoftDeleteColumnsMixin,
)


class Project(CreatedUpdatedServerTimestampsMixin, SoftDeleteColumnsMixin, Base):
    __tablename__ = "projects"

    team = relationship("Team", lazy="joined")

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(
        String(10), unique=True, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    issue_sequence: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
