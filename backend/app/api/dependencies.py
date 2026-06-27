"""Shared FastAPI dependencies."""
from app.db.repositories.task_repository import TaskRepository


def get_task_repository(*args, **kwargs) -> TaskRepository:
    """Dependency that provides a bound TaskRepository."""
    return TaskRepository()
