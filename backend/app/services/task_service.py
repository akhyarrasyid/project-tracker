import datetime

from sqlalchemy import func
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, lazyload

from app.db.models.project import Project
from app.db.models.task import Task
from app.db.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.activity_service import ActivityLoggerService

STATUS_TODO = "Todo"
STATUS_IN_PROGRESS = "In Progress"
STATUS_DONE = "Done"
STATUS_REVIEW = "Review"
RANK_STEP = 1024


class TaskService:
    @staticmethod
    def _rebalance_column(
        db: Session, project_id: int, status: str, exclude_task_id: int | None = None
    ) -> None:
        query = (
            db.query(Task)
            .options(
                lazyload(Task.project),
                lazyload(Task.sprint_relation),
                lazyload(Task.assignee_relation),
                lazyload(Task.creator),
            )
            .filter(
                Task.project_id == project_id,
                Task.status == status,
                Task.deleted_at.is_(None),
            )
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
    def validate_and_apply_status_transition(
        db: Session, task: Task, new_status: str, actor_id: int, is_admin: bool = False
    ) -> None:
        if is_admin:
            return

        old_status = task.status
        if old_status == new_status:
            return

        # Allowed main transitions: Todo -> In Progress -> Review -> Done
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
        if data["status"] == STATUS_DONE:
            data["progress_percentage"] = 100
            data["completed_at"] = datetime.datetime.now(datetime.timezone.utc)
            data["completed_by_id"] = creator_id
        elif data["progress_percentage"] == 100:
            data["status"] = STATUS_DONE
            data["completed_at"] = datetime.datetime.now(datetime.timezone.utc)
            data["completed_by_id"] = creator_id
        elif 0 < data["progress_percentage"] < 100 and data["status"] not in (
            STATUS_IN_PROGRESS,
            STATUS_REVIEW,
        ):
            data["status"] = STATUS_IN_PROGRESS

    @staticmethod
    def _sync_status_and_progress_update(
        updates: dict, task: Task, actor_id: int
    ) -> None:
        old_status = task.status
        new_status = updates.get("status", old_status)
        new_progress = updates.get("progress_percentage", task.progress_percentage)

        # Auto sync: status Done -> progress 100%
        if "status" in updates and new_status == STATUS_DONE:
            updates["progress_percentage"] = 100
            updates["completed_at"] = datetime.datetime.now(datetime.timezone.utc)
            updates["completed_by_id"] = actor_id

        # Auto sync: progress 100% -> status Done
        elif "progress_percentage" in updates and new_progress == 100:
            updates["status"] = STATUS_DONE
            updates["completed_at"] = datetime.datetime.now(datetime.timezone.utc)
            updates["completed_by_id"] = actor_id

        # Auto sync: 1-99% progress -> status In Progress/Review
        elif "progress_percentage" in updates and 0 < new_progress < 100:
            if new_status not in (STATUS_IN_PROGRESS, STATUS_REVIEW):
                updates["status"] = STATUS_IN_PROGRESS

        # Clean completed fields if transitioned back from Done
        if (
            "status" in updates
            and new_status != STATUS_DONE
            and old_status == STATUS_DONE
        ):
            updates["completed_at"] = None
            updates["completed_by_id"] = None

    @staticmethod
    def create_task(
        db: Session, project_id: int, task_in: TaskCreate, creator_id: int, commit: bool = True
    ) -> Task:
        data = task_in.model_dump()

        # Enforce progress sync on creation
        TaskService._sync_status_and_progress_create(data, creator_id)

        issue_number = TaskService._allocate_issue_number(db, project_id)
        task = Task(
            project_id=project_id,
            created_by_id=creator_id,
            number=issue_number,
            rank=TaskService._get_next_rank(db, project_id, data["status"]),
            **data,
        )
        db.add(task)
        if commit:
            db.commit()
            db.refresh(task)
        else:
            db.flush()

        # Log creation
        ActivityLoggerService.log(
            db,
            actor_id=creator_id,
            action="Task Created",
            task_id=task.id,
            project_id=project_id,
        )
        return task

    @staticmethod
    def move_task(
        db: Session,
        task_id: int,
        target_status: str,
        actor_id: int,
        before_issue_id: int | None = None,
        after_issue_id: int | None = None,
    ) -> Task:
        if before_issue_id is not None and after_issue_id is not None and before_issue_id == after_issue_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="before_issue_id and after_issue_id must reference different issues",
            )

        task = (
            db.query(Task)
            .options(
                lazyload(Task.project),
                lazyload(Task.sprint_relation),
                lazyload(Task.assignee_relation),
                lazyload(Task.creator),
            )
            .filter(Task.id == task_id, Task.deleted_at.is_(None))
            .with_for_update()
            .one_or_none()
        )
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        actor = db.query(User).filter(User.id == actor_id).first()
        is_admin = actor.role == "admin" if actor else False
        TaskService.validate_and_apply_status_transition(
            db, task, target_status, actor_id, is_admin=is_admin
        )

        before_task = None
        after_task = None
        if before_issue_id is not None:
            before_task = (
                db.query(Task)
                .options(
                    lazyload(Task.project),
                    lazyload(Task.sprint_relation),
                    lazyload(Task.assignee_relation),
                    lazyload(Task.creator),
                )
                .filter(
                    Task.id == before_issue_id,
                    Task.project_id == task.project_id,
                    Task.status == target_status,
                    Task.deleted_at.is_(None),
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
                db.query(Task)
                .options(
                    lazyload(Task.project),
                    lazyload(Task.sprint_relation),
                    lazyload(Task.assignee_relation),
                    lazyload(Task.creator),
                )
                .filter(
                    Task.id == after_issue_id,
                    Task.project_id == task.project_id,
                    Task.status == target_status,
                    Task.deleted_at.is_(None),
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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The requested insertion window is stale",
            )

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
        task.status = target_status
        task.rank = assign_rank()
        TaskService._sync_status_and_progress_update({"status": target_status}, task, actor_id)

        db.commit()
        db.refresh(task)

        if old_status != task.status:
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
        return task

    @staticmethod
    def update_task(
        db: Session, task: Task, task_in: TaskUpdate, actor_id: int
    ) -> Task:
        updates = task_in.model_dump(exclude_unset=True)

        # Track old values for activity log
        old_status = task.status
        old_progress = task.progress_percentage
        old_assignee = task.assignee_id
        old_priority = task.priority
        old_is_blocked = task.is_blocked
        old_blocked_reason = task.blocked_reason

        # Handle progress and status synchronization
        new_status = updates.get("status", task.status)

        # Check if actor is admin
        actor = db.query(User).filter(User.id == actor_id).first()
        is_admin = actor.role == "admin" if actor else False

        # Enforce transitions
        if "status" in updates:
            TaskService.validate_and_apply_status_transition(
                db, task, new_status, actor_id, is_admin=is_admin
            )

        TaskService._sync_status_and_progress_update(updates, task, actor_id)

        # Apply updates
        for field, value in updates.items():
            setattr(task, field, value)

        db.commit()
        db.refresh(task)

        # Log changes
        if old_status != task.status:
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
        if old_progress != task.progress_percentage:
            ActivityLoggerService.log(
                db,
                actor_id=actor_id,
                action="Progress Changed",
                task_id=task.id,
                project_id=task.project_id,
                field="progress_percentage",
                old_val=str(old_progress),
                new_val=str(task.progress_percentage),
            )
        if old_assignee != task.assignee_id:
            ActivityLoggerService.log(
                db,
                actor_id=actor_id,
                action="Assignee Changed",
                task_id=task.id,
                project_id=task.project_id,
                field="assignee_id",
                old_val=str(old_assignee),
                new_val=str(task.assignee_id),
            )
        if old_priority != task.priority:
            ActivityLoggerService.log(
                db,
                actor_id=actor_id,
                action="Priority Changed",
                task_id=task.id,
                project_id=task.project_id,
                field="priority",
                old_val=old_priority,
                new_val=task.priority,
            )
        if old_is_blocked != task.is_blocked:
            ActivityLoggerService.log(
                db,
                actor_id=actor_id,
                action="Blocked State Changed",
                task_id=task.id,
                project_id=task.project_id,
                field="is_blocked",
                old_val=str(old_is_blocked),
                new_val=str(task.is_blocked),
            )
        if old_blocked_reason != task.blocked_reason:
            ActivityLoggerService.log(
                db,
                actor_id=actor_id,
                action="Blocked Reason Changed",
                task_id=task.id,
                project_id=task.project_id,
                field="blocked_reason",
                old_val=old_blocked_reason,
                new_val=task.blocked_reason,
            )

        return task

    @staticmethod
    def soft_delete_task(db: Session, task: Task, actor_id: int) -> None:
        task.deleted_at = datetime.datetime.now(datetime.timezone.utc)
        task.deleted_by_id = actor_id
        db.commit()

        # Log deletion
        ActivityLoggerService.log(
            db,
            actor_id=actor_id,
            action="Task Deleted",
            task_id=task.id,
            project_id=task.project_id,
        )
