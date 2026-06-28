from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Label(Base):
    __tablename__ = "labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6B7280")
