from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import check_project_access, get_current_user
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.models.task import Task
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.task import TaskResponse

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=List[ProjectResponse])
def list_projects(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.role == "admin":
        return db.query(Project).filter(Project.deleted_at.is_(None)).all()

    # Worker can only see projects they are assigned to
    return (
        db.query(Project)
        .join(ProjectMember, Project.id == ProjectMember.project_id)
        .filter(ProjectMember.user_id == current_user.id, Project.deleted_at.is_(None))
        .all()
    )


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can create projects",
        )

    # Check unique key
    exists = db.query(Project).filter(Project.key == payload.key).first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project with this key already exists",
        )

    project = Project(
        name=payload.name,
        key=payload.key,
        description=payload.description,
        team_id=payload.team_id,
        status="ACTIVE",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Auto-add the admin as project owner
    pm = ProjectMember(
        project_id=project.id, user_id=current_user.id, project_role="OWNER"
    )
    db.add(pm)
    db.commit()

    return project


@router.get("/{id}", response_model=ProjectResponse)
def get_project(
    id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    project, _ = check_project_access(db, current_user, id, min_role="VIEWER")
    return project


@router.get("/{id}/tasks", response_model=List[TaskResponse])
def get_project_tasks(
    id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    check_project_access(db, current_user, id, min_role="VIEWER")
    return db.query(Task).filter(Task.project_id == id, Task.deleted_at.is_(None)).all()
