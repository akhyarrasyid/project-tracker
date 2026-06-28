from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.department import Department
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.models.team import Team
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.meta import (
    DepartmentResponse,
    ProjectMetaResponse,
    TeamResponse,
    UserMetaResponse,
)

router = APIRouter(prefix="/meta", tags=["metadata"])


@router.get("/departments", response_model=List[DepartmentResponse])
def get_departments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Admin sees all, worker sees only their own department (or let's let all users read departments to drive dropdowns)
    return db.query(Department).all()


@router.get("/teams", response_model=List[TeamResponse])
def get_teams(
    department_id: Optional[int] = Query(None),
    db: Annotated[Session, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    query = db.query(Team)
    if department_id is not None:
        query = query.filter(Team.department_id == department_id)
    return query.all()


@router.get("/projects", response_model=List[ProjectMetaResponse])
def get_projects(
    team_id: Optional[int] = Query(None),
    db: Annotated[Session, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    query = db.query(Project).filter(Project.deleted_at.is_(None))
    if team_id is not None:
        query = query.filter(Project.team_id == team_id)

    # Workers are restricted to projects they are member of, unless admin
    projects = query.all()
    if current_user.role == "admin":
        return projects

    # Get project IDs the user belongs to
    user_project_ids = [
        pm.project_id
        for pm in db.query(ProjectMember)
        .filter(ProjectMember.user_id == current_user.id)
        .all()
    ]
    return [p for p in projects if p.id in user_project_ids]


@router.get("/users", response_model=List[UserMetaResponse])
def get_users(
    project_id: Optional[int] = Query(None),
    db: Annotated[Session, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    if project_id is not None:
        # Get users belonging to project members
        query = (
            db.query(User)
            .join(ProjectMember, User.id == ProjectMember.user_id)
            .filter(ProjectMember.project_id == project_id, User.deleted_at.is_(None))
        )
        return query.all()

    # Fallback to team members or all users
    return db.query(User).filter(User.deleted_at.is_(None)).all()
