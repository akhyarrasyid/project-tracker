import datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.project_member import ProjectMember
from app.db.models.task import Task
from app.db.models.user import User
from app.db.models.watcher import Watcher


class WatcherService:
    @staticmethod
    def _load_task(db: Session, issue_id: int) -> Task:
        task = (
            db.query(Task)
            .filter(Task.id == issue_id, Task.deleted_at.is_(None))
            .one_or_none()
        )
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Issue {issue_id} not found",
            )
        return task

    @staticmethod
    def _load_user(db: Session, user_id: int) -> User:
        user = (
            db.query(User)
            .filter(User.id == user_id, User.deleted_at.is_(None), User.is_active.is_(True))
            .one_or_none()
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        return user

    @staticmethod
    def _has_project_access(db: Session, project_id: int, user_id: int) -> bool:
        member = (
            db.query(ProjectMember)
            .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
            .one_or_none()
        )
        user = WatcherService._load_user(db, user_id)
        return user.role == "admin" or member is not None

    @staticmethod
    def _ensure_member_can_be_watched(db: Session, project_id: int, user_id: int) -> None:
        if not WatcherService._has_project_access(db, project_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Watcher must have project access",
            )

    @staticmethod
    def can_manage_others(actor: User, membership: ProjectMember | None) -> bool:
        if actor.role == "admin":
            return True
        return membership is not None and membership.project_role == "OWNER"

    @staticmethod
    def refresh_watchers_count(db: Session, issue_id: int) -> int:
        total = (
            db.query(func.count())
            .select_from(Watcher)
            .filter(Watcher.task_id == issue_id, Watcher.is_watching.is_(True))
            .scalar()
            or 0
        )
        task = WatcherService._load_task(db, issue_id)
        task.watchers_count = total
        db.flush()
        return total

    @staticmethod
    def ensure_watcher(
        db: Session,
        *,
        issue_id: int,
        user_id: int,
        actor_id: int | None,
        auto: bool = False,
    ) -> tuple[Watcher | None, bool]:
        task = WatcherService._load_task(db, issue_id)
        if not WatcherService._has_project_access(db, task.project_id, user_id):
            if auto:
                return None, False
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Watcher must have project access",
            )

        watcher = (
            db.query(Watcher)
            .filter(Watcher.task_id == issue_id, Watcher.user_id == user_id)
            .with_for_update(of=Watcher)
            .one_or_none()
        )
        if watcher is None:
            watcher = Watcher(
                task_id=issue_id,
                user_id=user_id,
                added_by_id=actor_id,
                is_watching=True,
                unwatched_at=None,
            )
            db.add(watcher)
            db.flush()
            WatcherService.refresh_watchers_count(db, issue_id)
            return watcher, True

        if watcher.is_watching:
            return watcher, False

        if auto:
            return watcher, False

        watcher.is_watching = True
        watcher.unwatched_at = None
        watcher.added_by_id = actor_id
        db.flush()
        WatcherService.refresh_watchers_count(db, issue_id)
        return watcher, True

    @staticmethod
    def disable_watcher(
        db: Session,
        *,
        issue_id: int,
        user_id: int,
        actor_id: int | None,
    ) -> tuple[Watcher, bool]:
        task = WatcherService._load_task(db, issue_id)
        WatcherService._ensure_member_can_be_watched(db, task.project_id, user_id)
        watcher = (
            db.query(Watcher)
            .filter(Watcher.task_id == issue_id, Watcher.user_id == user_id)
            .with_for_update(of=Watcher)
            .one_or_none()
        )
        if watcher is None:
            watcher = Watcher(
                task_id=issue_id,
                user_id=user_id,
                added_by_id=actor_id,
                is_watching=False,
                unwatched_at=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(watcher)
            db.flush()
            WatcherService.refresh_watchers_count(db, issue_id)
            return watcher, True

        if not watcher.is_watching:
            return watcher, False

        watcher.is_watching = False
        watcher.unwatched_at = datetime.datetime.now(datetime.timezone.utc)
        db.flush()
        WatcherService.refresh_watchers_count(db, issue_id)
        return watcher, True

    @staticmethod
    def list_active_watchers(db: Session, issue_id: int) -> list[Watcher]:
        return (
            db.query(Watcher)
            .filter(Watcher.task_id == issue_id, Watcher.is_watching.is_(True))
            .order_by(Watcher.created_at.asc(), Watcher.user_id.asc())
            .all()
        )
