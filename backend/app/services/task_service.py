import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, lazyload

from app.db.models.activity_log import ActivityLog
from app.db.models.project import Project
from app.db.models.task import Task
from app.db.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.activity_service import ActivityLoggerService

STATUS_TODO = "Todo"
STATUS_IN_PROGRESS = "In Progress"
STATUS_DONE = "Done"
STATUS_BLOCKED = "Blocked"
STATUS_REVIEW = "Review"


class TaskService:
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
    def get_last_non_blocked_status(db: Session, task_id: int) -> str:
        # Query activity logs for status changes
        log = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.task_id == task_id,
                ActivityLog.field == "status",
                ActivityLog.new_value != STATUS_BLOCKED,
            )
            .order_by(ActivityLog.created_at.desc())
            .first()
        )

        if log and log.new_value:
            return log.new_value
        return STATUS_TODO

    @staticmethod
    def validate_and_apply_status_transition(
        db: Session, task: Task, new_status: str, actor_id: int, is_admin: bool = False
    ) -> None:
        if is_admin:
            return

        old_status = task.status
        if old_status == new_status:
            return

        # Any -> Blocked is always allowed
        if new_status == STATUS_BLOCKED:
            return

        # Blocked -> previous state
        if old_status == STATUS_BLOCKED:
            prev_status = TaskService.get_last_non_blocked_status(db, task.id)
            if new_status != prev_status:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot transition from Blocked to '{new_status}'. Must return to previous state '{prev_status}'.",
                )
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
            STATUS_BLOCKED,
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
            if new_status not in (STATUS_IN_PROGRESS, STATUS_REVIEW, STATUS_BLOCKED):
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
    def update_task(
        db: Session, task: Task, task_in: TaskUpdate, actor_id: int
    ) -> Task:
        updates = task_in.model_dump(exclude_unset=True)

        # Track old values for activity log
        old_status = task.status
        old_progress = task.progress_percentage
        old_assignee = task.assignee_id
        old_priority = task.priority

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
