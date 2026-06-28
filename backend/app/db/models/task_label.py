from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class TaskLabel(Base):
    __tablename__ = "task_labels"

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True
    )
    label_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("labels.id", ondelete="CASCADE"),
        primary_key=True
    )
