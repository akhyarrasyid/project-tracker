"""Shared FastAPI dependencies."""
import math
from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.repositories.task_repository import TaskRepository


def get_task_repository(db: Session = Depends(get_db)) -> TaskRepository:
    """Dependency that provides a bound TaskRepository.

    Currently TaskRepository uses static methods and doesn't hold state,
    so this is a no-op shim. When we move to instance-based repos this
    becomes the DI seam.
    """
    return TaskRepository()
