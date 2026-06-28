"""TaskRepository — data access layer with pagination, filtering, sorting, search."""

from typing import Any, List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models.department import Department
from app.db.models.project import Project
from app.db.models.task import Task
from app.db.models.team import Team
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


class MergedFilters:
    def __init__(self, filters: Any, kwargs: dict):
        self._filters = filters
        self._kwargs = kwargs

    def __getattr__(self, name: str) -> Any:
        if name in self._kwargs:
            return self._kwargs[name]
        if self._filters is not None:
            if isinstance(self._filters, dict):
                return self._filters.get(name)
            return getattr(self._filters, name, None)
        return None


class TaskRepository:
    """All DB operations for the Task aggregate."""

    # ── Read ──────────────────────────────────────────────────────────────────

    @staticmethod
    def get_by_id(db: Session, task_id: int) -> Optional[Task]:
        return (
            db.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()
        )

    @staticmethod
    def _apply_joins(q, filters: Any):
        joined_team = False
        if filters.team_id or filters.department_id or filters.department or filters.team:
            q = q.join(Project, Task.project_id == Project.id)
        if filters.department_id or filters.department:
            q = q.join(Team, Project.team_id == Team.id)
            joined_team = True
        if filters.department:
            q = q.join(Department, Team.department_id == Department.id)
        if filters.team and not joined_team:
            q = q.join(Team, Project.team_id == Team.id)
        if filters.assignee:
            from app.db.models.user import User

            q = q.join(User, Task.assignee_id == User.id)
        if filters.sprint:
            from app.db.models.sprint import Sprint

            q = q.join(Sprint, Task.sprint_id == Sprint.id)
        return q

    @staticmethod
    def _apply_filters(q, filters: Any, allowed_project_ids: Optional[List[int]]):
        if allowed_project_ids is not None:
            q = q.filter(Task.project_id.in_(allowed_project_ids))
        if filters.status:
            statuses = [s.strip() for s in filters.status.split(",")]
            q = q.filter(Task.status.in_(statuses))
        if filters.priority:
            priorities = [p.strip() for p in filters.priority.split(",")]
            q = q.filter(Task.priority.in_(priorities))
        if filters.project_id is not None:
            q = q.filter(Task.project_id == filters.project_id)
        if filters.sprint_id is not None:
            q = q.filter(Task.sprint_id == filters.sprint_id)
        if filters.assignee_id is not None:
            q = q.filter(Task.assignee_id == filters.assignee_id)
        if filters.team_id is not None:
            q = q.filter(Project.team_id == filters.team_id)
        if filters.department_id is not None:
            q = q.filter(Team.department_id == filters.department_id)
        if filters.department:
            q = q.filter(Department.name == filters.department)
        if filters.assignee:
            from app.db.models.user import User

            q = q.filter(or_(User.full_name == filters.assignee, User.username == filters.assignee))
        if filters.team:
            q = q.filter(Team.name == filters.team)
        if filters.sprint:
            from app.db.models.sprint import Sprint

            q = q.filter(Sprint.name == filters.sprint)
        if filters.quarter:
            q = q.filter(Task.quarter == filters.quarter)
        if filters.risk_level:
            q = q.filter(Task.risk_level == filters.risk_level)
        return q

    @staticmethod
    def _apply_search(q, filters: Any):
        if filters.search:
            term = f"%{filters.search}%"
            q = q.filter(
                or_(
                    Task.title.ilike(term),
                    Task.description.ilike(term),
                )
            )
        return q

    @staticmethod
    def _apply_sort(q, filters: Any):
        sort_by = filters.sort_by or "created_at"
        sort_order = filters.sort_order or "desc"
        sort_col = _SORTABLE_COLUMNS.get(sort_by, Task.created_at)
        if sort_order == "asc":
            q = q.order_by(sort_col.asc())
        else:
            q = q.order_by(sort_col.desc())
        return q

    @staticmethod
    def list(
        db: Session,
        filters: Optional[Any] = None,
        allowed_project_ids: Optional[List[int]] = None,
        **kwargs,
    ) -> Tuple[List[Task], int]:
        """Return (items, total) with optional filtering, search and pagination."""
        merged_filters = MergedFilters(filters, kwargs)
        q = db.query(Task).filter(Task.deleted_at.is_(None))
        q = TaskRepository._apply_joins(q, merged_filters)
        q = TaskRepository._apply_filters(q, merged_filters, allowed_project_ids)
        q = TaskRepository._apply_search(q, merged_filters)

        total: int = q.count()

        q = TaskRepository._apply_sort(q, merged_filters)

        # pagination
        page = merged_filters.page or 1
        size = merged_filters.size or 20
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
