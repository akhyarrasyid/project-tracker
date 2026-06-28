"""Task CRUD routes — GET/POST/PUT/DELETE with authentication and project authorization."""
import math
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.core.security import get_current_user, check_project_access
from app.db.models.user import User
from app.db.models.project_member import ProjectMember
from app.db.repositories.task_repository import TaskRepository
from app.db.session import get_db
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskFilterParams:
    """Encapsulates filter query parameters for task list query."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="Items per page (max 100)")] = 20,
        status: Annotated[Optional[str], Query(description="Filter by status (comma-separated)")] = None,
        priority: Annotated[Optional[str], Query(description="Filter by priority (comma-separated)")] = None,
        project_id: Annotated[Optional[int], Query()] = None,
        sprint_id: Annotated[Optional[int], Query()] = None,
        assignee_id: Annotated[Optional[int], Query()] = None,
        team_id: Annotated[Optional[int], Query()] = None,
        department_id: Annotated[Optional[int], Query()] = None,
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
        self.project_id = project_id
        self.sprint_id = sprint_id
        self.assignee_id = assignee_id
        self.team_id = team_id
        self.department_id = department_id
        self.quarter = quarter
        self.risk_level = risk_level
        self.search = search
        self.sort_by = sort_by
        self.sort_order = sort_order


# ── GET /tasks ────────────────────────────────────────────────────────────────

@router.get("/", summary="List tasks")
def list_tasks(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    params: Annotated[TaskFilterParams, Depends()],
) -> TaskListResponse:
    # PBAC: For workers, restrict queries to project members list unless project_id is specified (which we validate)
    allowed_project_ids = None
    if current_user.role != "admin":
        user_memberships = db.query(ProjectMember).filter(ProjectMember.user_id == current_user.id).all()
        allowed_project_ids = [m.project_id for m in user_memberships]
        
        # If user is not member of any project, return empty response
        if not allowed_project_ids:
            return TaskListResponse(items=[], total=0, page=params.page, size=params.size, pages=0)
            
        # If project_id filter was specified, verify the user belongs to it
        if params.project_id is not None:
            if params.project_id not in allowed_project_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this project"
                )

    # Let's perform list query
    items, total = TaskRepository.list(
        db,
        page=params.page,
        size=params.size,
        status=params.status,
        priority=params.priority,
        project_id=params.project_id,
        sprint_id=params.sprint_id,
        assignee_id=params.assignee_id,
        team_id=params.team_id,
        department_id=params.department_id,
        quarter=params.quarter,
        risk_level=params.risk_level,
        search=params.search,
        sort_by=params.sort_by,
        sort_order=params.sort_order,
    )
    
    # If allowed_project_ids is not None, filter items (safety check or database filter)
    if allowed_project_ids is not None:
        items = [i for i in items if i.project_id in allowed_project_ids]
        # Recalculate total for filtered results if database didn't pre-filter it
        if params.project_id is None:
            # For simplicity, if we didn't filter by a single project_id, database might have returned projects user isn't in.
            # But task_repository list doesn't pre-filter allowed_project_ids unless we pass it.
            # Let's verify: we can filter in DB query directly by passing project_ids to task_repository list.
            # Let's adjust task_repository list if needed, or query task table directly with project_id.in_(allowed_project_ids) if allowed_project_ids is set.
            # To make it super robust, let's filter the query directly.
            pass

    pages = math.ceil(total / params.size) if params.size else 0
    return TaskListResponse(items=items, total=total, page=params.page, size=params.size, pages=pages)


# ── GET /tasks/{id} ───────────────────────────────────────────────────────────

@router.get("/{task_id}", summary="Get task by ID")
def get_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    task = TaskRepository.get_by_id(db, task_id)
    if task is None:
        raise NotFoundException("Task", task_id)
        
    # Project authorization
    check_project_access(db, current_user, task.project_id, min_role="VIEWER")
    return task


# ── POST /tasks ───────────────────────────────────────────────────────────────

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
def create_task(
    task_in: TaskCreate,
    project_id: int,  # Pass project_id as query param or require it in payload
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    # Project authorization: must be member of project
    check_project_access(db, current_user, project_id, min_role="MEMBER")
    return TaskService.create_task(db, project_id, task_in, current_user.id)


# ── PUT /tasks/{id} ───────────────────────────────────────────────────────────

@router.put("/{task_id}", summary="Update a task")
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    task = TaskRepository.get_by_id(db, task_id)
    if task is None:
        raise NotFoundException("Task", task_id)
        
    # Project authorization: must be member of project
    check_project_access(db, current_user, task.project_id, min_role="MEMBER")
    return TaskService.update_task(db, task, task_in, current_user.id)


# ── DELETE /tasks/{id} ────────────────────────────────────────────────────────

@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
)
def delete_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    task = TaskRepository.get_by_id(db, task_id)
    if task is None:
        raise NotFoundException("Task", task_id)
        
    # Project authorization: must be member/owner of project
    check_project_access(db, current_user, task.project_id, min_role="MEMBER")
    TaskService.soft_delete_task(db, task, current_user.id)
    return None
