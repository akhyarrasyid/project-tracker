"""Canonical issue routes with task compatibility."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.task_routes import TaskFilterParams, create_task, list_tasks
from app.core.exceptions import NotFoundException
from app.core.security import check_project_access, get_current_user
from app.db.models.activity_log import ActivityLog
from app.db.models.comment import Comment
from app.db.models.user import User
from app.db.repositories.task_repository import TaskRepository
from app.db.session import get_db
from app.schemas.issue import (
    IssueActivityResponse,
    IssueCommentCreate,
    IssueCommentResponse,
    IssueUpdateRequest,
)
from app.schemas.notification import IssueWatchersResponse
from app.schemas.task import (
    IssueMoveRequest,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from app.services.notification_service import NotificationService
from app.services.task_service import TaskService
from app.services.watcher_service import WatcherService

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


def _resolve_issue_by_id(issue_id: int, db: Session):
    task = TaskRepository.get_by_id(db, issue_id)
    if task is None:
        raise NotFoundException("Issue", issue_id)
    return task


@router.get("/", summary="List issues")
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
)
def create_issue(
    issue_in: TaskCreate,
    project_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    return create_task(issue_in, project_id, db, current_user)


@router.patch("/{issue_id:int}", summary="Update an issue")
def patch_issue(
    issue_id: int,
    issue_in: IssueUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    task = _resolve_issue_by_id(issue_id, db)
    check_project_access(db, current_user, task.project_id, min_role="MEMBER")
    task_update = TaskUpdate(
        **issue_in.model_dump(exclude_unset=True, exclude={"expected_version"})
    )
    return TaskService.update_task(
        db,
        task,
        task_update,
        current_user.id,
        expected_version=issue_in.expected_version,
    )


@router.get("/{issue_id:int}/comments", summary="List issue comments")
def list_issue_comments(
    issue_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[IssueCommentResponse]:
    task = _resolve_issue_by_id(issue_id, db)
    check_project_access(db, current_user, task.project_id, min_role="VIEWER")
    comments = (
        db.query(Comment)
        .filter(Comment.task_id == issue_id, Comment.deleted_at.is_(None))
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .all()
    )
    return comments


@router.post(
    "/{issue_id:int}/comments",
    status_code=status.HTTP_201_CREATED,
    summary="Create issue comment",
)
def create_issue_comment(
    issue_id: int,
    payload: IssueCommentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IssueCommentResponse:
    task = _resolve_issue_by_id(issue_id, db)
    check_project_access(db, current_user, task.project_id, min_role="MEMBER")
    comment = TaskService.create_comment(
        db,
        task_id=issue_id,
        author_id=current_user.id,
        content=payload.content,
        parent_id=payload.parent_id,
    )
    return comment


@router.get(
    "/{issue_id:int}/activities",
    summary="List issue activities",
)
def list_issue_activities(
    issue_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[IssueActivityResponse]:
    task = _resolve_issue_by_id(issue_id, db)
    check_project_access(db, current_user, task.project_id, min_role="VIEWER")
    activities = (
        db.query(ActivityLog)
        .filter(ActivityLog.task_id == issue_id)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .all()
    )
    return activities


@router.get(
    "/{issue_id:int}/watchers",
    summary="List issue watchers",
)
def list_issue_watchers(
    issue_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IssueWatchersResponse:
    task = _resolve_issue_by_id(issue_id, db)
    _, membership = check_project_access(db, current_user, task.project_id, min_role="VIEWER")
    payload = NotificationService.build_watchers_payload(
        db,
        issue=task,
        current_user=current_user,
        can_manage_watchers=WatcherService.can_manage_others(current_user, membership),
    )
    return IssueWatchersResponse(**payload)


@router.post(
    "/{issue_id:int}/watchers/me",
    summary="Watch an issue",
)
def watch_issue_me(
    issue_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IssueWatchersResponse:
    task = _resolve_issue_by_id(issue_id, db)
    _, membership = check_project_access(db, current_user, task.project_id, min_role="VIEWER")
    WatcherService.ensure_watcher(
        db,
        issue_id=task.id,
        user_id=current_user.id,
        actor_id=current_user.id,
        auto=False,
    )
    db.commit()
    payload = NotificationService.build_watchers_payload(
        db,
        issue=task,
        current_user=current_user,
        can_manage_watchers=WatcherService.can_manage_others(current_user, membership),
    )
    return IssueWatchersResponse(**payload)


@router.delete(
    "/{issue_id:int}/watchers/me",
    summary="Unwatch an issue",
)
def unwatch_issue_me(
    issue_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IssueWatchersResponse:
    task = _resolve_issue_by_id(issue_id, db)
    _, membership = check_project_access(db, current_user, task.project_id, min_role="VIEWER")
    WatcherService.disable_watcher(
        db,
        issue_id=task.id,
        user_id=current_user.id,
        actor_id=current_user.id,
    )
    db.commit()
    payload = NotificationService.build_watchers_payload(
        db,
        issue=task,
        current_user=current_user,
        can_manage_watchers=WatcherService.can_manage_others(current_user, membership),
    )
    return IssueWatchersResponse(**payload)


@router.post(
    "/{issue_id:int}/watchers/{user_id:int}",
    summary="Add another watcher to an issue",
)
def add_issue_watcher(
    issue_id: int,
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IssueWatchersResponse:
    task = _resolve_issue_by_id(issue_id, db)
    _, membership = check_project_access(db, current_user, task.project_id, min_role="VIEWER")
    if not WatcherService.can_manage_others(current_user, membership):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient project permissions",
        )
    watcher, created = WatcherService.ensure_watcher(
        db,
        issue_id=task.id,
        user_id=user_id,
        actor_id=current_user.id,
        auto=False,
    )
    if created:
        NotificationService.notify_watcher_added(
            db,
            issue=task,
            actor_id=current_user.id,
            recipient_id=watcher.user_id,
        )
    db.commit()
    payload = NotificationService.build_watchers_payload(
        db,
        issue=task,
        current_user=current_user,
        can_manage_watchers=True,
    )
    return IssueWatchersResponse(**payload)


@router.delete(
    "/{issue_id:int}/watchers/{user_id:int}",
    summary="Remove another watcher from an issue",
)
def remove_issue_watcher(
    issue_id: int,
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IssueWatchersResponse:
    task = _resolve_issue_by_id(issue_id, db)
    _, membership = check_project_access(db, current_user, task.project_id, min_role="VIEWER")
    if not WatcherService.can_manage_others(current_user, membership):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient project permissions",
        )
    WatcherService.disable_watcher(
        db,
        issue_id=task.id,
        user_id=user_id,
        actor_id=current_user.id,
    )
    db.commit()
    payload = NotificationService.build_watchers_payload(
        db,
        issue=task,
        current_user=current_user,
        can_manage_watchers=True,
    )
    return IssueWatchersResponse(**payload)


@router.get("/{issue_id:int}", summary="Get issue by id")
def get_issue_by_id(
    issue_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    task = _resolve_issue_by_id(issue_id, db)
    check_project_access(db, current_user, task.project_id, min_role="VIEWER")
    return task


@router.get("/{issue_key}", summary="Get issue by key")
def get_issue(
    issue_key: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    task = _resolve_issue(issue_key, db)
    check_project_access(db, current_user, task.project_id, min_role="VIEWER")
    return task


@router.put("/{issue_key}", summary="Update an issue")
def update_issue(
    issue_key: str,
    issue_in: TaskUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    task = _resolve_issue(issue_key, db)
    check_project_access(db, current_user, task.project_id, min_role="MEMBER")
    return TaskService.update_task(db, task, issue_in, current_user.id)


@router.patch(
    "/{issue_id:int}/move",
    summary="Move an issue on the board",
)
def move_issue(
    issue_id: int,
    payload: IssueMoveRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    task = TaskRepository.get_by_id(db, issue_id)
    if task is None:
        raise NotFoundException("Issue", issue_id)

    check_project_access(db, current_user, task.project_id, min_role="MEMBER")
    return TaskService.move_task(
        db,
        task_id=issue_id,
        target_status=payload.status.value,
        actor_id=current_user.id,
        before_issue_id=payload.before_issue_id,
        after_issue_id=payload.after_issue_id,
        expected_version=payload.expected_version,
    )


@router.delete(
    "/{issue_id:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an issue by id",
)
def delete_issue_by_id(
    issue_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    task = _resolve_issue_by_id(issue_id, db)
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
