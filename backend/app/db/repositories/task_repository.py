"""TaskRepository — data access layer with pagination, filtering, sorting, search."""
import math
from typing import List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


_SORTABLE_COLUMNS = {
    "id": Task.id,
    "title": Task.title,
    "status": Task.status,
    "priority": Task.priority,
    "due_date": Task.due_date,
    "created_at": Task.created_at,
    "updated_at": Task.updated_at,
    "story_points": Task.story_points,
    "progress_percentage": Task.progress_percentage,
}


class TaskRepository:
    """All DB operations for the Task aggregate."""

    # ── Read ──────────────────────────────────────────────────────────────────

    @staticmethod
    def get_by_id(db: Session, task_id: int) -> Optional[Task]:
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        page: int = 1,
        size: int = 20,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        department: Optional[str] = None,
        assignee: Optional[str] = None,
        team: Optional[str] = None,
        sprint: Optional[str] = None,
        quarter: Optional[str] = None,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Task], int]:
        """Return (items, total) with optional filtering, search and pagination."""
        q = db.query(Task)

        # ── Filters ───────────────────────────────────────────────────────────
        if status:
            statuses = [s.strip() for s in status.split(",")]
            q = q.filter(Task.status.in_(statuses))
        if priority:
            priorities = [p.strip() for p in priority.split(",")]
            q = q.filter(Task.priority.in_(priorities))
        if department:
            q = q.filter(Task.department == department)
        if assignee:
            q = q.filter(Task.assignee == assignee)
        if team:
            q = q.filter(Task.team == team)
        if sprint:
            q = q.filter(Task.sprint == sprint)
        if quarter:
            q = q.filter(Task.quarter == quarter)
        if risk_level:
            q = q.filter(Task.risk_level == risk_level)

        # ── Full-text search on title and description ─────────────────────────
        if search:
            term = f"%{search}%"
            q = q.filter(
                or_(
                    Task.title.ilike(term),
                    Task.description.ilike(term),
                )
            )

        total: int = q.count()

        # ── Sort ──────────────────────────────────────────────────────────────
        sort_col = _SORTABLE_COLUMNS.get(sort_by, Task.created_at)
        if sort_order == "asc":
            q = q.order_by(sort_col.asc())
        else:
            q = q.order_by(sort_col.desc())

        # ── Paginate ──────────────────────────────────────────────────────────
        offset = (page - 1) * size
        items = q.offset(offset).limit(size).all()

        return items, total

    # ── Write ─────────────────────────────────────────────────────────────────

    @staticmethod
    def create(db: Session, task_in: TaskCreate) -> Task:
        data = task_in.model_dump()
        task = Task(**data)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def update(db: Session, task: Task, task_in: TaskUpdate) -> Task:
        updates = task_in.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(task, field, value)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def delete(db: Session, task: Task) -> None:
        db.delete(task)
        db.commit()

    # ── Bulk ──────────────────────────────────────────────────────────────────

    @staticmethod
    def bulk_create(db: Session, tasks_data: List[dict]) -> int:
        """Insert many tasks in a single transaction. Returns count inserted."""
        tasks = [Task(**data) for data in tasks_data]
        db.bulk_save_objects(tasks)
        db.commit()
        return len(tasks)
