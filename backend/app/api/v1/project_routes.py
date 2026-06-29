import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.security import check_project_access, get_current_user
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.models.task import Task
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectSummaryResponse,
)
from app.schemas.task import BoardColumnResponse, ProjectBoardResponse, TaskResponse

router = APIRouter(prefix="/projects", tags=["projects"])
BOARD_STATUSES = ("Todo", "In Progress", "Review", "Done")


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


@router.get("/{id}/board", response_model=ProjectBoardResponse)
def get_project_board(
    id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 50,
    status: Optional[str] = None,
    before: Optional[int] = None,
    after: Optional[int] = None,
    start: bool = True,
    end: bool = False,
):
    check_project_access(db, current_user, id, min_role="VIEWER")

    if before is not None and after is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="before and after cannot be used together",
        )
    if start and end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start and end cannot both be true",
        )

    statuses = (status,) if status else BOARD_STATUSES
    columns = {}
    for column_status in statuses:
        if column_status not in BOARD_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported board status '{column_status}'",
            )

        base_query = db.query(Task).filter(
            Task.project_id == id,
            Task.status == column_status,
            Task.deleted_at.is_(None),
        )
        total_count = base_query.count()

        ordered = base_query.order_by(Task.rank.asc(), Task.id.asc())
        if end:
            ordered = base_query.order_by(Task.rank.desc(), Task.id.desc())
        if after is not None:
            ordered = ordered.filter(Task.rank > after)
        if before is not None:
            ordered = ordered.filter(Task.rank < before)

        items = ordered.limit(min(limit, 100)).all()
        if end:
            items = list(reversed(items))

        next_after = items[-1].rank if items and len(items) < total_count else None
        next_before = items[0].rank if items and len(items) < total_count else None

        columns[column_status] = BoardColumnResponse(
            status=column_status,
            items=[TaskResponse.model_validate(item) for item in items],
            total_count=total_count,
            next_after=next_after,
            next_before=next_before,
        )

    return ProjectBoardResponse(columns=columns)


@router.get("/{id}/summary", response_model=ProjectSummaryResponse)
def get_project_summary(
    id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    check_project_access(db, current_user, id, min_role="VIEWER")

    today = datetime.date.today()
    at_risk_predicate = or_(
        Task.risk_level == "High",
        and_(Task.due_date <= today + datetime.timedelta(days=3), Task.status != "Done"),
        and_(
            Task.is_blocked.is_(True),
            Task.due_date <= today + datetime.timedelta(days=7),
        ),
    )

    base_query = db.query(Task).filter(Task.project_id == id, Task.deleted_at.is_(None))
    total_issues = base_query.count()
    done_issues = base_query.filter(Task.status == "Done").count()
    active_issues = base_query.filter(Task.status != "Done").count()
    blocked_count = base_query.filter(Task.is_blocked.is_(True)).count()
    overdue_count = base_query.filter(
        Task.due_date < today,
        Task.status != "Done",
    ).count()
    at_risk_count = base_query.filter(at_risk_predicate).count()

    total_story_points = (
        base_query.with_entities(func.coalesce(func.sum(Task.story_points), 0)).scalar()
        or 0
    )
    done_story_points = (
        base_query.filter(Task.status == "Done")
        .with_entities(func.coalesce(func.sum(Task.story_points), 0))
        .scalar()
        or 0
    )

    issue_progress_percent = (
        round((done_issues / total_issues) * 100) if total_issues else 0
    )
    point_progress_percent = (
        round((done_story_points / total_story_points) * 100)
        if total_story_points
        else 0
    )

    return ProjectSummaryResponse(
        total_issues=total_issues,
        done_issues=done_issues,
        active_issues=active_issues,
        issue_progress_percent=issue_progress_percent,
        point_progress_percent=point_progress_percent,
        blocked_count=blocked_count,
        overdue_count=overdue_count,
        at_risk_count=at_risk_count,
    )
