import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, lazyload

from app.db.models.comment import Comment
from app.db.models.project import Project
from app.db.models.task import Task
from app.db.models.user import User
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.activity_service import ActivityLoggerService
from app.services.notification_service import NotificationService
from app.services.watcher_service import WatcherService

STATUS_TODO = "Todo"
STATUS_IN_PROGRESS = "In Progress"
STATUS_DONE = "Done"
STATUS_REVIEW = "Review"
RANK_STEP = 1024


class TaskService:
    @staticmethod
    def _task_query(db: Session):
        return (
            db.query(Task)
            .options(
                lazyload(Task.project),
                lazyload(Task.sprint_relation),
                lazyload(Task.assignee_relation),
                lazyload(Task.creator),
            )
            .filter(Task.deleted_at.is_(None))
        )

    @staticmethod
    def _serialize_task_summary(task: Task) -> dict[str, Any]:
        return TaskResponse.model_validate(task).model_dump(mode="json")

    @staticmethod
    def _raise_stale_issue(task: Task, message: str = "Issue version is stale") -> None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": message,
                "latest_issue": TaskService._serialize_task_summary(task),
            },
        )

    @staticmethod
    def _load_task_for_update(db: Session, task_id: int) -> Task:
        task = TaskService._task_query(db).filter(Task.id == task_id).with_for_update().one_or_none()
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )
        return task

    @staticmethod
    def _ensure_expected_version(task: Task, expected_version: int | None) -> None:
        if expected_version is None:
            return
        if task.version != expected_version:
            TaskService._raise_stale_issue(task)

    @staticmethod
    def _rebalance_column(
        db: Session, project_id: int, status: str, exclude_task_id: int | None = None
    ) -> None:
        query = (
            TaskService._task_query(db)
            .filter(Task.project_id == project_id, Task.status == status)
            .order_by(Task.rank.asc(), Task.id.asc())
            .with_for_update()
        )
        if exclude_task_id is not None:
            query = query.filter(Task.id != exclude_task_id)

        for index, item in enumerate(query.all(), start=1):
            item.rank = index * RANK_STEP
        db.flush()

    @staticmethod
    def _get_next_rank(db: Session, project_id: int, status: str) -> int:
        max_rank = (
            db.query(func.max(Task.rank))
            .filter(
                Task.project_id == project_id,
                Task.status == status,
                Task.deleted_at.is_(None),
            )
            .scalar()
        )
        return (max_rank or 0) + RANK_STEP

    @staticmethod
    def _allocate_issue_number(db: Session, project_id: int) -> int:
        project = (
            db.query(Project)
            .options(lazyload(Project.team))
            .filter(Project.id == project_id, Project.deleted_at.is_(None))
            .with_for_update()
            .one()
        )
        project.issue_sequence += 1
        return project.issue_sequence

    @staticmethod
    def _validate_parent(db: Session, task: Task | None, project_id: int, parent_id: int | None) -> None:
        if parent_id is None:
            return
        if task is not None and task.id == parent_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Issue cannot be its own parent",
            )

        parent = TaskService._task_query(db).filter(Task.id == parent_id).one_or_none()
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Parent issue not found",
            )
        if parent.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Parent issue must belong to the same project",
            )
        if task is None:
            return

        current = parent
        visited: set[int] = set()
        while current.parent_id is not None:
            if current.parent_id == task.id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Circular issue hierarchy is not allowed",
                )
            if current.parent_id in visited:
                break
            visited.add(current.parent_id)
            current = TaskService._task_query(db).filter(Task.id == current.parent_id).one_or_none()
            if current is None:
                break

    @staticmethod
    def validate_and_apply_status_transition(
        db: Session, task: Task, new_status: str, actor_id: int, is_admin: bool = False
    ) -> None:
        del db, actor_id
        if is_admin:
            return

        old_status = task.status
        if old_status == new_status:
            return

        allowed = {
            STATUS_TODO: {STATUS_IN_PROGRESS},
            STATUS_IN_PROGRESS: {STATUS_REVIEW},
            STATUS_REVIEW: {STATUS_DONE},
        }

        if new_status not in allowed.get(old_status, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from '{old_status}' to '{new_status}'.",
            )

    @staticmethod
    def _sync_status_and_progress_create(data: dict, creator_id: int) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        if data["status"] == STATUS_DONE:
            data["progress_percentage"] = 100
            data["completed_at"] = now
            data["completed_by_id"] = creator_id
        elif data["progress_percentage"] == 100:
            data["status"] = STATUS_DONE
            data["completed_at"] = now
            data["completed_by_id"] = creator_id
        elif 0 < data["progress_percentage"] < 100 and data["status"] not in (
            STATUS_IN_PROGRESS,
            STATUS_REVIEW,
        ):
            data["status"] = STATUS_IN_PROGRESS

        if data.get("is_blocked") is False:
            data["blocked_reason"] = None

    @staticmethod
    def _sync_status_and_progress_update(updates: dict, task: Task, actor_id: int) -> None:
        old_status = task.status
        new_status = updates.get("status", old_status)
        new_progress = updates.get("progress_percentage", task.progress_percentage)
        now = datetime.datetime.now(datetime.timezone.utc)

        if "status" in updates and new_status == STATUS_DONE:
            updates["progress_percentage"] = 100
            updates["completed_at"] = now
            updates["completed_by_id"] = actor_id
        elif "progress_percentage" in updates and new_progress == 100:
            updates["status"] = STATUS_DONE
            updates["completed_at"] = now
            updates["completed_by_id"] = actor_id
        elif "progress_percentage" in updates and 0 < new_progress < 100:
            if new_status not in (STATUS_IN_PROGRESS, STATUS_REVIEW):
                updates["status"] = STATUS_IN_PROGRESS

        if "status" in updates and new_status != STATUS_DONE and old_status == STATUS_DONE:
            updates["completed_at"] = None
            updates["completed_by_id"] = None

        if updates.get("is_blocked") is False and "blocked_reason" not in updates:
            updates["blocked_reason"] = None

    @staticmethod
    def _get_actor(db: Session, actor_id: int) -> User | None:
        return db.query(User).filter(User.id == actor_id).first()

    @staticmethod
    def _build_change_map(task: Task, updates: dict[str, Any]) -> dict[str, tuple[Any, Any]]:
        changes: dict[str, tuple[Any, Any]] = {}
        for field, new_value in updates.items():
            old_value = getattr(task, field)
            if old_value != new_value:
                changes[field] = (old_value, new_value)
        return changes

    @staticmethod
    def _log_task_changes(
        db: Session, task: Task, actor_id: int, changes: dict[str, tuple[Any, Any]]
    ) -> None:
        action_map = {
            "status": "Status Changed",
            "priority": "Priority Changed",
            "assignee_id": "Assignee Changed",
            "due_date": "Due Date Changed",
            "is_blocked": "Blocked State Changed",
            "blocked_reason": "Blocked Reason Changed",
            "description": "Description Changed",
            "parent_id": "Parent Changed",
            "progress_percentage": "Progress Changed",
            "title": "Title Changed",
        }
        for field, (old_value, new_value) in changes.items():
            action = action_map.get(field)
            if action is None:
                continue
            ActivityLoggerService.log(
                db,
                actor_id=actor_id,
                action=action,
                task_id=task.id,
                project_id=task.project_id,
                field=field,
                old_val=None if old_value is None else str(old_value),
                new_val=None if new_value is None else str(new_value),
            )

    @staticmethod
    def create_task(
        db: Session,
        project_id: int,
        task_in: TaskCreate,
        creator_id: int,
        commit: bool = True,
    ) -> Task:
        data = task_in.model_dump()
        TaskService._validate_parent(db, None, project_id, data.get("parent_id"))
        TaskService._sync_status_and_progress_create(data, creator_id)

        task = Task(
            project_id=project_id,
            created_by_id=creator_id,
            number=TaskService._allocate_issue_number(db, project_id),
            rank=TaskService._get_next_rank(db, project_id, data["status"]),
            **data,
        )
        db.add(task)
        db.flush()

        ActivityLoggerService.log(
            db,
            actor_id=creator_id,
            action="Task Created",
            task_id=task.id,
            project_id=project_id,
        )
        WatcherService.ensure_watcher(
            db,
            issue_id=task.id,
            user_id=creator_id,
            actor_id=creator_id,
            auto=True,
        )
        if task.assignee_id is not None:
            WatcherService.ensure_watcher(
                db,
                issue_id=task.id,
                user_id=task.assignee_id,
                actor_id=creator_id,
                auto=True,
            )
            NotificationService.notify_issue_assigned(
                db,
                issue=task,
                actor_id=creator_id,
                assignee_id=task.assignee_id,
            )

        if commit:
            db.commit()
            db.refresh(task)
        return task

    @staticmethod
    def move_task(
        db: Session,
        task_id: int,
        target_status: str,
        actor_id: int,
        before_issue_id: int | None = None,
        after_issue_id: int | None = None,
        expected_version: int | None = None,
    ) -> Task:
        if (
            before_issue_id is not None
            and after_issue_id is not None
            and before_issue_id == after_issue_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="before_issue_id and after_issue_id must reference different issues",
            )

        task = TaskService._load_task_for_update(db, task_id)
        TaskService._ensure_expected_version(task, expected_version)

        actor = TaskService._get_actor(db, actor_id)
        is_admin = actor.role == "admin" if actor else False
        TaskService.validate_and_apply_status_transition(
            db, task, target_status, actor_id, is_admin=is_admin
        )

        before_task = None
        after_task = None
        if before_issue_id is not None:
            before_task = (
                TaskService._task_query(db)
                .filter(
                    Task.id == before_issue_id,
                    Task.project_id == task.project_id,
                    Task.status == target_status,
                )
                .with_for_update()
                .one_or_none()
            )
            if before_task is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="before_issue_id is not available in the target column",
                )
        if after_issue_id is not None:
            after_task = (
                TaskService._task_query(db)
                .filter(
                    Task.id == after_issue_id,
                    Task.project_id == task.project_id,
                    Task.status == target_status,
                )
                .with_for_update()
                .one_or_none()
            )
            if after_task is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="after_issue_id is not available in the target column",
                )

        if (
            before_task is not None
            and after_task is not None
            and after_task.rank >= before_task.rank
        ):
            TaskService._raise_stale_issue(task, "The requested insertion window is stale")

        def assign_rank() -> int:
            if before_task is None and after_task is None:
                return TaskService._get_next_rank(db, task.project_id, target_status)
            if before_task is not None and after_task is None:
                if before_task.rank <= 1:
                    TaskService._rebalance_column(
                        db, task.project_id, target_status, exclude_task_id=task.id
                    )
                    db.refresh(before_task)
                return max(1, before_task.rank // 2)
            if before_task is None and after_task is not None:
                return after_task.rank + RANK_STEP

            assert before_task is not None
            assert after_task is not None
            gap = before_task.rank - after_task.rank
            if gap <= 1:
                TaskService._rebalance_column(
                    db, task.project_id, target_status, exclude_task_id=task.id
                )
                db.refresh(before_task)
                db.refresh(after_task)
            return (before_task.rank + after_task.rank) // 2

        old_status = task.status
        old_rank = task.rank
        original_version = task.version
        move_updates = {"status": target_status}
        TaskService._sync_status_and_progress_update(move_updates, task, actor_id)

        task.rank = assign_rank()
        for field, value in move_updates.items():
            setattr(task, field, value)

        if old_status == task.status and old_rank == task.rank:
            return task

        task.version = original_version + 1
        changes: dict[str, tuple[Any, Any]] = {}
        if old_status != task.status:
            changes["status"] = (old_status, task.status)
            ActivityLoggerService.log(
                db,
                actor_id=actor_id,
                action="Status Changed",
                task_id=task.id,
                project_id=task.project_id,
                field="status",
                old_val=old_status,
                new_val=task.status,
            )
        if old_rank != task.rank:
            ActivityLoggerService.log(
                db,
                actor_id=actor_id,
                action="Issue Reordered",
                task_id=task.id,
                project_id=task.project_id,
                field="rank",
                old_val=str(old_rank),
                new_val=str(task.rank),
            )
        NotificationService.notify_issue_updated(
            db,
            issue=task,
            actor_id=actor_id,
            changes=changes,
        )

        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def update_task(
        db: Session,
        task: Task,
        task_in: TaskUpdate,
        actor_id: int,
        expected_version: int | None = None,
    ) -> Task:
        locked_task = TaskService._load_task_for_update(db, task.id)
        TaskService._ensure_expected_version(locked_task, expected_version)

        updates = task_in.model_dump(exclude_unset=True)
        if not updates:
            return locked_task

        actor = TaskService._get_actor(db, actor_id)
        is_admin = actor.role == "admin" if actor else False
        new_status = updates.get("status", locked_task.status)

        if "status" in updates:
            TaskService.validate_and_apply_status_transition(
                db, locked_task, new_status, actor_id, is_admin=is_admin
            )
        if "parent_id" in updates:
            TaskService._validate_parent(
                db, locked_task, locked_task.project_id, updates.get("parent_id")
            )

        TaskService._sync_status_and_progress_update(updates, locked_task, actor_id)
        changes = TaskService._build_change_map(locked_task, updates)
        if not changes:
            return locked_task

        for field, value in updates.items():
            setattr(locked_task, field, value)

        locked_task.version += 1
        TaskService._log_task_changes(db, locked_task, actor_id, changes)
        NotificationService.notify_issue_updated(
            db,
            issue=locked_task,
            actor_id=actor_id,
            changes=changes,
        )
        db.commit()
        db.refresh(locked_task)
        return locked_task

    @staticmethod
    def create_comment(
        db: Session, task_id: int, author_id: int, content: str, parent_id: int | None = None
    ) -> Comment:
        task = TaskService._load_task_for_update(db, task_id)
        if parent_id is not None:
            parent_comment = (
                db.query(Comment)
                .filter(
                    Comment.id == parent_id,
                    Comment.task_id == task.id,
                    Comment.deleted_at.is_(None),
                )
                .one_or_none()
            )
            if parent_comment is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Parent comment not found",
                )
        comment = Comment(
            task_id=task.id,
            author_id=author_id,
            content=content,
            parent_id=parent_id,
        )
        db.add(comment)
        task.comments_count += 1
        task.version += 1
        db.flush()

        ActivityLoggerService.log(
            db,
            actor_id=author_id,
            action="Comment Created",
            task_id=task.id,
            project_id=task.project_id,
            field="comment",
            new_val=content,
        )
        NotificationService.notify_issue_comment(
            db,
            issue=task,
            actor_id=author_id,
            comment=comment,
        )
        db.commit()
        db.refresh(comment)
        db.refresh(task)
        return comment

    @staticmethod
    def soft_delete_task(db: Session, task: Task, actor_id: int) -> None:
        locked_task = TaskService._load_task_for_update(db, task.id)
        locked_task.deleted_at = datetime.datetime.now(datetime.timezone.utc)
        locked_task.deleted_by_id = actor_id
        locked_task.version += 1
        ActivityLoggerService.log(
            db,
            actor_id=actor_id,
            action="Task Deleted",
            task_id=locked_task.id,
            project_id=locked_task.project_id,
        )
        db.commit()
