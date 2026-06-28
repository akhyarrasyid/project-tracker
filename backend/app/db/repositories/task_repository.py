"""TaskRepository — data access layer with pagination, filtering, sorting, search."""
import math
from typing import List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models.task import Task
from app.db.models.project import Project
from app.db.models.team import Team
from app.db.models.department import Department
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
        return db.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()

    @staticmethod
    def list(
        db: Session,
        *,
        page: int = 1,
        size: int = 20,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project_id: Optional[int] = None,
        sprint_id: Optional[int] = None,
        assignee_id: Optional[int] = None,
        team_id: Optional[int] = None,
        department_id: Optional[int] = None,
        quarter: Optional[str] = None,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
        allowed_project_ids: Optional[List[int]] = None,
        **kwargs,
    ) -> Tuple[List[Task], int]:
        """Return (items, total) with optional filtering, search and pagination."""
        q = db.query(Task).filter(Task.deleted_at.is_(None))

        # ── Relationships joins if needed ─────────────────────────────────────
        if team_id or department_id:
            q = q.join(Project, Task.project_id == Project.id)
        if department_id:
            q = q.join(Team, Project.team_id == Team.id)

        # ── Filters ───────────────────────────────────────────────────────────
        if allowed_project_ids is not None:
            q = q.filter(Task.project_id.in_(allowed_project_ids))
        if status:
            statuses = [s.strip() for s in status.split(",")]
            q = q.filter(Task.status.in_(statuses))
        if priority:
            priorities = [p.strip() for p in priority.split(",")]
            q = q.filter(Task.priority.in_(priorities))
        if project_id is not None:
            q = q.filter(Task.project_id == project_id)
        if sprint_id is not None:
            q = q.filter(Task.sprint_id == sprint_id)
        if assignee_id is not None:
            q = q.filter(Task.assignee_id == assignee_id)
        if team_id is not None:
            q = q.filter(Project.team_id == team_id)
        if department_id is not None:
            q = q.filter(Team.department_id == department_id)
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
        sort_by = kwargs.get("sort_by", "created_at")
        sort_order = kwargs.get("sort_order", "desc")
        sort_col = _SORTABLE_COLUMNS.get(sort_by, Task.created_at)
        if sort_order == "asc":
            q = q.order_by(sort_col.asc())
        else:
            q = q.order_by(sort_col.desc())

        # ── Paginate ──────────────────────────────────────────────────────────
        offset = (page - 1) * size
        items = q.offset(offset).limit(size).all()

        return items, total
