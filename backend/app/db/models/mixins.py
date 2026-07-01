import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class CreatedUpdatedServerTimestampsMixin:
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteColumnsMixin:
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @declared_attr
    def deleted_by_id(cls) -> Mapped[Optional[int]]:
        return mapped_column(
            Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )
