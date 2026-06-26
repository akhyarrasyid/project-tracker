import datetime
from sqlalchemy.orm import Session
from models import Task
from schemas import TaskCreate, TaskUpdate

class TaskRepository:
    @staticmethod
    def get_all(db: Session):
        return db.query(Task).order_by(Task.id.desc()).all()

    @staticmethod
    def get_by_id(db: Session, task_id: int):
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def create(db: Session, task_in: TaskCreate) -> Task:
        db_task = Task(
            title=task_in.title,
            description=task_in.description,
            status=task_in.status
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return db_task

    @staticmethod
    def update(db: Session, db_task: Task, task_in: TaskUpdate) -> Task:
        # Pydantic model_dump(exclude_unset=True) gets only the client-supplied values.
        update_data = task_in.model_dump(exclude_unset=True)
        
        # Ensure ID can't be mutated.
        update_data.pop("id", None)
        
        for key, value in update_data.items():
            setattr(db_task, key, value)
            
        # Update timestamp.
        db_task.updated_at = datetime.datetime.now(datetime.timezone.utc)
        
        db.commit()
        db.refresh(db_task)
        return db_task

    @staticmethod
    def delete(db: Session, db_task: Task) -> None:
        db.delete(db_task)
        db.commit()
