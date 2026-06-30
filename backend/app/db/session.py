from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def _build_connect_args(database_url: str, schema: str | None) -> dict:
    connect_args: dict = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return connect_args

    if schema:
        connect_args["options"] = f"-csearch_path={schema}"
    return connect_args


connect_args = _build_connect_args(settings.DATABASE_URL, settings.DATABASE_SCHEMA)
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """Dependency for database session lifecycle management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
