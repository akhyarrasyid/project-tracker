"""Task CRUD routes — GET/POST/PUT/DELETE with authentication and project authorization."""

import math
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.core.security import check_project_access, get_current_user
from app.db.models.project_member import ProjectMember
from app.db.models.user import User
from app.db.repositories.task_repository import TaskRepository
from app.db.session import get_db
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


class PaginationParams:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
        size: Annotated[
            int, Query(ge=1, le=100, description="Items per page (max 100)")
        ] = 20,
    ):
        self.page = page
        self.size = size


class SearchSortParams:
    def __init__(
        self,
        search: Annotated[
            Optional[str], Query(description="Search title and description")
        ] = None,
        sort_by: Annotated[str, Query(description="Field to sort by")] = "created_at",
        sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    ):
        self.search = search
        self.sort_by = sort_by
        self.sort_order = sort_order


class TaskCoreFilters:
    def __init__(
        self,
        status: Annotated[
            Optional[str], Query(description="Filter by status (comma-separated)")
        ] = None,
        priority: Annotated[
            Optional[str], Query(description="Filter by priority (comma-separated)")
        ] = None,
        project_id: Annotated[Optional[int], Query()] = None,
        sprint_id: Annotated[Optional[int], Query()] = None,
        assignee_id: Annotated[Optional[int], Query()] = None,
        team_id: Annotated[Optional[int], Query()] = None,
        department_id: Annotated[Optional[int], Query()] = None,
        quarter: Annotated[Optional[str], Query()] = None,
        risk_level: Annotated[Optional[str], Query()] = None,
    ):
        self.status = status
        self.priority = priority
        self.project_id = project_id
        self.sprint_id = sprint_id
        self.assignee_id = assignee_id
        self.team_id = team_id
        self.department_id = department_id
        self.quarter = quarter
        self.risk_level = risk_level


class LegacyFilters:
    def __init__(
        self,
        department: Annotated[Optional[str], Query()] = None,
        assignee: Annotated[Optional[str], Query()] = None,
        team: Annotated[Optional[str], Query()] = None,
        sprint: Annotated[Optional[str], Query()] = None,
    ):
        self.department = department
        self.assignee = assignee
        self.team = team
        self.sprint = sprint


class TaskFilterParams:
    """Combines all sub-filters into a single parameter object for clean signature and repo interface."""

    def __init__(
        self,
        pagination: Annotated[PaginationParams, Depends()],
        sorting: Annotated[SearchSortParams, Depends()],
        core: Annotated[TaskCoreFilters, Depends()],
        legacy: Annotated[LegacyFilters, Depends()],
    ):
        self.page = pagination.page
        self.size = pagination.size
        self.search = sorting.search
        self.sort_by = sorting.sort_by
        self.sort_order = sorting.sort_order
        self.status = core.status
        self.priority = core.priority
        self.project_id = core.project_id
        self.sprint_id = core.sprint_id
        self.assignee_id = core.assignee_id
        self.team_id = core.team_id
        self.department_id = core.department_id
        self.quarter = core.quarter
        self.risk_level = core.risk_level
        self.department = legacy.department
        self.assignee = legacy.assignee
        self.team = legacy.team
        self.sprint = legacy.sprint


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
        user_memberships = (
            db.query(ProjectMember)
            .filter(ProjectMember.user_id == current_user.id)
            .all()
        )
        allowed_project_ids = [m.project_id for m in user_memberships]

        # If user is not member of any project, return empty response
        if not allowed_project_ids:
            return TaskListResponse(
                items=[], total=0, page=params.page, size=params.size, pages=0
            )

        # If project_id filter was specified, verify the user belongs to it
        if params.project_id is not None:
            if params.project_id not in allowed_project_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this project",
                )

    # Let's perform list query
    items, total = TaskRepository.list(
        db,
        filters=params,
        allowed_project_ids=allowed_project_ids,
    )

    pages = math.ceil(total / params.size) if params.size else 0
    items_response = [TaskResponse.model_validate(item) for item in items]
    return TaskListResponse(
        items=items_response,
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )


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
