"""Canonical issue routes with task compatibility."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.task_routes import TaskFilterParams, create_task, list_tasks
from app.core.exceptions import NotFoundException
from app.core.security import check_project_access, get_current_user
from app.db.models.user import User
from app.db.repositories.task_repository import TaskRepository
from app.db.session import get_db
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/issues", tags=["issues"])


def _resolve_issue(issue_key: str, db: Session):
    project_key, separator, issue_number_raw = issue_key.partition("-")
    if not separator or not project_key or not issue_number_raw.isdigit():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue '{issue_key}' not found",
        )

    task = TaskRepository.get_by_issue_key(db, project_key, int(issue_number_raw))
    if task is None:
        raise NotFoundException("Issue", issue_key)
    return task


@router.get("/", summary="List issues", response_model=TaskListResponse)
def list_issues(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    params: Annotated[TaskFilterParams, Depends()],
) -> TaskListResponse:
    return list_tasks(db, current_user, params)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new issue",
    response_model=TaskResponse,
)
def create_issue(
    issue_in: TaskCreate,
    project_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    return create_task(issue_in, project_id, db, current_user)


@router.get("/{issue_key}", summary="Get issue by key", response_model=TaskResponse)
def get_issue(
    issue_key: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    task = _resolve_issue(issue_key, db)
    check_project_access(db, current_user, task.project_id, min_role="VIEWER")
    return task


@router.put("/{issue_key}", summary="Update an issue", response_model=TaskResponse)
def update_issue(
    issue_key: str,
    issue_in: TaskUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    task = _resolve_issue(issue_key, db)
    check_project_access(db, current_user, task.project_id, min_role="MEMBER")
    return TaskService.update_task(db, task, issue_in, current_user.id)


@router.delete(
    "/{issue_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an issue",
)
def delete_issue(
    issue_key: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    task = _resolve_issue(issue_key, db)
    _, membership = check_project_access(
        db, current_user, task.project_id, min_role="MEMBER"
    )
    if (
        current_user.role != "admin"
        and membership is not None
        and membership.project_role == "MEMBER"
        and (task.created_by_id != current_user.id or task.status == "Done")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Members may only delete their own unfinished issues",
        )
    TaskService.soft_delete_task(db, task, current_user.id)
    return None
