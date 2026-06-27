"""Task CRUD routes — GET/POST/PUT/DELETE with pagination, filtering, sorting."""
import math
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.db.repositories.task_repository import TaskRepository
from app.db.session import get_db
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskFilterParams:
    """Encapsulates filter query parameters for task list query."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="Items per page (max 100)")] = 20,
        status: Annotated[Optional[str], Query(description="Filter by status (comma-separated)")] = None,
        priority: Annotated[Optional[str], Query(description="Filter by priority (comma-separated)")] = None,
        department: Annotated[Optional[str], Query()] = None,
        assignee: Annotated[Optional[str], Query()] = None,
        team: Annotated[Optional[str], Query()] = None,
        sprint: Annotated[Optional[str], Query()] = None,
        quarter: Annotated[Optional[str], Query()] = None,
        risk_level: Annotated[Optional[str], Query()] = None,
        search: Annotated[Optional[str], Query(description="Search title and description")] = None,
        sort_by: Annotated[str, Query(description="Field to sort by")] = "created_at",
        sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    ):
        self.page = page
        self.size = size
        self.status = status
        self.priority = priority
        self.department = department
        self.assignee = assignee
        self.team = team
        self.sprint = sprint
        self.quarter = quarter
        self.risk_level = risk_level
        self.search = search
        self.sort_by = sort_by
        self.sort_order = sort_order


# ── GET /tasks ────────────────────────────────────────────────────────────────

@router.get("/", summary="List tasks")
def list_tasks(
    db: Annotated[Session, Depends(get_db)],
    params: Annotated[TaskFilterParams, Depends()],
) -> TaskListResponse:
    items, total = TaskRepository.list(
        db,
        page=params.page,
        size=params.size,
        status=params.status,
        priority=params.priority,
        department=params.department,
        assignee=params.assignee,
        team=params.team,
        sprint=params.sprint,
        quarter=params.quarter,
        risk_level=params.risk_level,
        search=params.search,
        sort_by=params.sort_by,
        sort_order=params.sort_order,
    )
    pages = math.ceil(total / params.size) if params.size else 0
    return TaskListResponse(items=items, total=total, page=params.page, size=params.size, pages=pages)


# ── GET /tasks/{id} ───────────────────────────────────────────────────────────

@router.get("/{task_id}", summary="Get task by ID")
def get_task(task_id: int, db: Annotated[Session, Depends(get_db)]) -> TaskResponse:
    task = TaskRepository.get_by_id(db, task_id)
    if task is None:
        raise NotFoundException("Task", task_id)
    return task


# ── POST /tasks ───────────────────────────────────────────────────────────────

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
def create_task(task_in: TaskCreate, db: Annotated[Session, Depends(get_db)]) -> TaskResponse:
    return TaskRepository.create(db, task_in)


# ── PUT /tasks/{id} ───────────────────────────────────────────────────────────

@router.put("/{task_id}", summary="Update a task")
def update_task(
    task_id: int, task_in: TaskUpdate, db: Annotated[Session, Depends(get_db)]
) -> TaskResponse:
    task = TaskRepository.get_by_id(db, task_id)
    if task is None:
        raise NotFoundException("Task", task_id)
    return TaskRepository.update(db, task, task_in)


# ── DELETE /tasks/{id} ────────────────────────────────────────────────────────

@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
)
def delete_task(task_id: int, db: Annotated[Session, Depends(get_db)]) -> None:
    task = TaskRepository.get_by_id(db, task_id)
    if task is None:
        raise NotFoundException("Task", task_id)
    TaskRepository.delete(db, task)
    return None
