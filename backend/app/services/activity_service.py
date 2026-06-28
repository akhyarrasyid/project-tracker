from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.activity_log import ActivityLog

class ActivityLoggerService:
    @staticmethod
    def log(
        db: Session,
        *,
        actor_id: int,
        action: str,
        task_id: Optional[int] = None,
        project_id: Optional[int] = None,
        field: Optional[str] = None,
        old_val: Optional[str] = None,
        new_val: Optional[str] = None
    ) -> ActivityLog:
        log_entry = ActivityLog(
            actor_id=actor_id,
            action=action,
            task_id=task_id,
            project_id=project_id,
            field=field,
            old_value=old_val,
            new_value=new_val
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
