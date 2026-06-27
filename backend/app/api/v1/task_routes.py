"""Task CRUD routes — GET/POST/PUT/DELETE with pagination, filtering, sorting."""
import math
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.db.repositories.task_repository import TaskRepository
from app.db.session import get_db
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── GET /tasks ────────────────────────────────────────────────────────────────

@router.get("/", response_model=TaskListResponse, summary="List tasks")
def list_tasks(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    status: Optional[str] = Query(None, description="Filter by status (comma-separated)"),
    priority: Optional[str] = Query(None, description="Filter by priority (comma-separated)"),
    department: Optional[str] = Query(None),
    assignee: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    sprint: Optional[str] = Query(None),
    quarter: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search title and description"),
    sort_by: str = Query(default="created_at", description="Field to sort by"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> TaskListResponse:
    items, total = TaskRepository.list(
        db,
        page=page,
        size=size,
        status=status,
        priority=priority,
        department=department,
        assignee=assignee,
        team=team,
        sprint=sprint,
        quarter=quarter,
        risk_level=risk_level,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    pages = math.ceil(total / size) if size else 0
    return TaskListResponse(items=items, total=total, page=page, size=size, pages=pages)


# ── GET /tasks/{id} ───────────────────────────────────────────────────────────

@router.get("/{task_id}", response_model=TaskResponse, summary="Get task by ID")
def get_task(task_id: int, db: Session = Depends(get_db)) -> TaskResponse:
    task = TaskRepository.get_by_id(db, task_id)
    if task is None:
        raise NotFoundException("Task", task_id)
    return task


# ── POST /tasks ───────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
def create_task(task_in: TaskCreate, db: Session = Depends(get_db)) -> TaskResponse:
    return TaskRepository.create(db, task_in)


# ── PUT /tasks/{id} ───────────────────────────────────────────────────────────

@router.put("/{task_id}", response_model=TaskResponse, summary="Update a task")
def update_task(
    task_id: int, task_in: TaskUpdate, db: Session = Depends(get_db)
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
def delete_task(task_id: int, db: Session = Depends(get_db)) -> None:
    task = TaskRepository.get_by_id(db, task_id)
    if task is None:
        raise NotFoundException("Task", task_id)
    TaskRepository.delete(db, task)
    return None
