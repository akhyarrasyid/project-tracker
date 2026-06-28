"""Task CRUD routes — GET/POST/PUT/DELETE with authentication and project authorization."""

import csv
import datetime
import io
import math
from typing import Annotated, List, Optional, cast

from app.core.exceptions import NotFoundException
from app.core.security import check_project_access, get_current_user
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember
from app.db.models.team import Team
from app.db.models.user import User
from app.db.repositories.task_repository import TaskRepository
from app.db.session import get_db
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.services.task_service import TaskService
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/tasks", tags=["tasks"])


class PaginationParams:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
        size: Annotated[
            int, Query(ge=1, le=100, description="Items per page (max 100)")
        ] = 20,
    ):
        self.page = page
        self.size = size


class SearchSortParams:
    def __init__(
        self,
        search: Annotated[
            Optional[str], Query(description="Search title and description")
        ] = None,
        sort_by: Annotated[str, Query(description="Field to sort by")] = "created_at",
        sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    ):
        self.search = search
        self.sort_by = sort_by
        self.sort_order = sort_order


class TaskCoreFilters:
    def __init__(
        self,
        status: Annotated[
            Optional[str], Query(description="Filter by status (comma-separated)")
        ] = None,
        priority: Annotated[
            Optional[str], Query(description="Filter by priority (comma-separated)")
        ] = None,
        project_id: Annotated[Optional[int], Query()] = None,
        sprint_id: Annotated[Optional[int], Query()] = None,
        assignee_id: Annotated[Optional[int], Query()] = None,
        team_id: Annotated[Optional[int], Query()] = None,
        department_id: Annotated[Optional[int], Query()] = None,
        quarter: Annotated[Optional[str], Query()] = None,
        risk_level: Annotated[Optional[str], Query()] = None,
    ):
        self.status = status
        self.priority = priority
        self.project_id = project_id
        self.sprint_id = sprint_id
        self.assignee_id = assignee_id
        self.team_id = team_id
        self.department_id = department_id
        self.quarter = quarter
        self.risk_level = risk_level


class LegacyFilters:
    def __init__(
        self,
        department: Annotated[Optional[str], Query()] = None,
        assignee: Annotated[Optional[str], Query()] = None,
        team: Annotated[Optional[str], Query()] = None,
        sprint: Annotated[Optional[str], Query()] = None,
    ):
        self.department = department
        self.assignee = assignee
        self.team = team
        self.sprint = sprint


class TaskFilterParams:
    """Combines all sub-filters into a single parameter object for clean signature and repo interface."""

    def __init__(
        self,
        pagination: Annotated[PaginationParams, Depends()],
        sorting: Annotated[SearchSortParams, Depends()],
        core: Annotated[TaskCoreFilters, Depends()],
        legacy: Annotated[LegacyFilters, Depends()],
    ):
        self.page = pagination.page
        self.size = pagination.size
        self.search = sorting.search
        self.sort_by = sorting.sort_by
        self.sort_order = sorting.sort_order
        self.status = core.status
        self.priority = core.priority
        self.project_id = core.project_id
        self.sprint_id = core.sprint_id
        self.assignee_id = core.assignee_id
        self.team_id = core.team_id
        self.department_id = core.department_id
        self.quarter = core.quarter
        self.risk_level = core.risk_level
        self.department = legacy.department
        self.assignee = legacy.assignee
        self.team = legacy.team
        self.sprint = legacy.sprint


# ── GET /tasks ────────────────────────────────────────────────────────────────


@router.get("/", summary="List tasks")
def list_tasks(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    params: Annotated[TaskFilterParams, Depends()],
) -> TaskListResponse:
    # PBAC: For workers, restrict queries to project members list unless project_id is specified (which we validate)
    allowed_project_ids = None
    if current_user.role != "admin":
        user_memberships = (
            db.query(ProjectMember)
            .filter(ProjectMember.user_id == current_user.id)
            .all()
        )
        allowed_project_ids = [m.project_id for m in user_memberships]

        # If user is not member of any project, return empty response
        if not allowed_project_ids:
            return TaskListResponse(
                items=[], total=0, page=params.page, size=params.size, pages=0
            )

        # If project_id filter was specified, verify the user belongs to it
        if params.project_id is not None:
            if params.project_id not in allowed_project_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this project",
                )

    # Let's perform list query
    items, total = TaskRepository.list(
        db,
        filters=params,
        allowed_project_ids=allowed_project_ids,
    )

    pages = math.ceil(total / params.size) if params.size else 0
    items_response = [TaskResponse.model_validate(item) for item in items]
    return TaskListResponse(
        items=items_response,
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )

# ── CSV Import Endpoints ──────────────────────────────────────────────────────


@router.get("/import-template", summary="Download CSV template for task import")
def import_template(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    # Try to find a real project that matches user's department (if not admin)
    project = None
    if current_user.role != "admin":
        user_team = db.query(Team).filter(Team.id == current_user.team_id).first()
        if user_team:
            project = (
                db.query(Project)
                .join(Team, Project.team_id == Team.id)
                .filter(
                    Team.department_id == user_team.department_id,
                    Project.deleted_at.is_(None),
                )
                .first()
            )
    
    if not project:
        project = db.query(Project).filter(Project.deleted_at.is_(None)).first()

    proj_key = project.key if project else "FT"

    user = db.query(User).filter(User.deleted_at.is_(None)).first()
    user_email = user.email if user else "worker@example.com"

    headers = [
        "project_key",
        "title",
        "description",
        "status",
        "priority",
        "due_date",
        "story_points",
        "estimated_hours",
        "assignee_email",
        "tags",
    ]
    sample_row = [
        proj_key,
        "Implementasi Fitur Baru",
        "Deskripsi detail tugas baru",
        "Todo",
        "Medium",
        (datetime.date.today() + datetime.timedelta(days=7)).isoformat(),
        "3",
        "8",
        user_email,
        "frontend,feature",
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerow(sample_row)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=tasks_import_template.csv"
        },
    )


@router.post("/import-csv", summary="Import tasks from CSV file")
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        content = await file.read()
        csv_text = content.decode("utf-8-sig")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gagal membaca file: {str(e)}",
        )

    csv_file = io.StringIO(csv_text)
    reader = csv.DictReader(csv_file)

    expected_headers = {"project_key", "title"}
    if not reader.fieldnames or not expected_headers.issubset(
        set(reader.fieldnames)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header CSV tidak valid. Harus mengandung kolom: 'title' dan 'project_key'.",
        )

    errors = []
    tasks_to_create = []

    user_dept_id = None
    if current_user.role != "admin":
        user_team = db.query(Team).filter(Team.id == current_user.team_id).first()
        if user_team:
            user_dept_id = user_team.department_id

    for idx, row in enumerate(reader, start=2):
        proj_key_str = (
            row.get("project_key", "").strip() if "project_key" in row else ""
        )
        title = row.get("title", "").strip() if "title" in row else ""
        description = (
            row.get("description", "").strip() if "description" in row else ""
        )
        status_str = row.get("status", "").strip() if "status" in row else "Todo"
        priority_str = (
            row.get("priority", "").strip() if "priority" in row else "Medium"
        )
        due_date_str = row.get("due_date", "").strip() if "due_date" in row else ""
        sp_str = row.get("story_points", "").strip() if "story_points" in row else "1"
        est_hours_str = (
            row.get("estimated_hours", "").strip()
            if "estimated_hours" in row
            else "8"
        )
        assignee_email = (
            row.get("assignee_email", "").strip() if "assignee_email" in row else ""
        )
        tags_str = row.get("tags", "").strip() if "tags" in row else ""

        # 1. Project Lookup
        project = None
        if proj_key_str:
            project = (
                db.query(Project)
                .filter(Project.key == proj_key_str, Project.deleted_at.is_(None))
                .first()
            )

        if not project:
            errors.append(
                {
                    "row": idx,
                    "field": "project_key",
                    "message": "Proyek tidak ditemukan.",
                }
            )
            continue

        # 2. Department Boundary Validation
        if current_user.role != "admin":
            proj_team = db.query(Team).filter(Team.id == project.team_id).first()
            if not proj_team or proj_team.department_id != user_dept_id:
                errors.append(
                    {
                        "row": idx,
                        "field": "project_key",
                        "message": f"Anda tidak diizinkan membuat task untuk proyek '{project.name}' di departemen lain.",
                    }
                )
                continue

        # 3. Title Validation
        if not title:
            errors.append(
                {"row": idx, "field": "title", "message": "Judul task wajib diisi."}
            )
            continue

        # 4. Status Validation
        if status_str not in ["Todo", "In Progress", "Review", "Blocked", "Done"]:
            errors.append(
                {
                    "row": idx,
                    "field": "status",
                    "message": f"Status '{status_str}' tidak valid. Pilihan: Todo, In Progress, Review, Blocked, Done.",
                }
            )
            continue

        # 5. Priority Validation
        if priority_str not in ["Low", "Medium", "High", "Critical"]:
            errors.append(
                {
                    "row": idx,
                    "field": "priority",
                    "message": f"Prioritas '{priority_str}' tidak valid. Pilihan: Low, Medium, High, Critical.",
                }
            )
            continue

        # 6. Due Date Validation
        due_date = None
        if not due_date_str:
            due_date = datetime.date.today() + datetime.timedelta(days=7)
        else:
            try:
                due_date = datetime.datetime.strptime(due_date_str, "%Y-%m-%d").date()
            except ValueError:
                errors.append(
                    {
                        "row": idx,
                        "field": "due_date",
                        "message": "Format tanggal jatuh tempo salah. Gunakan format YYYY-MM-DD.",
                    }
                )
                continue

        # 7. Story Points Validation
        try:
            sp = int(sp_str)
            if sp not in [1, 2, 3, 5, 8, 13]:
                errors.append(
                    {
                        "row": idx,
                        "field": "story_points",
                        "message": "Story Points harus salah satu dari: 1, 2, 3, 5, 8, 13.",
                    }
                )
                continue
        except ValueError:
            errors.append(
                {
                    "row": idx,
                    "field": "story_points",
                    "message": "Story Points harus berupa angka.",
                }
            )
            continue

        # 8. Estimated Hours Validation
        try:
            est_hours = int(est_hours_str)
            if est_hours < 1:
                errors.append(
                    {
                        "row": idx,
                        "field": "estimated_hours",
                        "message": "Estimasi jam harus minimal 1.",
                    }
                )
                continue
        except ValueError:
            errors.append(
                {
                    "row": idx,
                    "field": "estimated_hours",
                    "message": "Estimasi jam harus berupa angka.",
                }
            )
            continue

        # 9. Assignee Email Validation
        assignee_id = None
        if assignee_email:
            assignee = (
                db.query(User)
                .filter(User.email == assignee_email, User.deleted_at.is_(None))
                .first()
            )
            if not assignee:
                errors.append(
                    {
                        "row": idx,
                        "field": "assignee_email",
                        "message": f"Pengguna dengan email '{assignee_email}' tidak ditemukan.",
                    }
                )
                continue
            assignee_id = assignee.id

        # 10. Tags Validation
        tags = []
        if tags_str:
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            if len(tags) > 4:
                errors.append(
                    {
                        "row": idx,
                        "field": "tags",
                        "message": "Maksimal 4 tag diperbolehkan.",
                    }
                )
                continue

        tasks_to_create.append(
            {
                "project_id": project.id,
                "title": title,
                "description": description,
                "status": status_str,
                "priority": priority_str,
                "due_date": due_date,
                "story_points": sp,
                "estimated_hours": est_hours,
                "assignee_id": assignee_id,
                "tags": tags,
            }
        )

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Gagal mengimpor CSV. Ditemukan kesalahan pada baris data.",
                "errors": errors,
            },
        )

    if not tasks_to_create:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak ada data task yang valid untuk diimpor.",
        )

    created_tasks = []
    try:
        for t_data in tasks_to_create:
            from app.schemas.task import TaskCreate as SchemaTaskCreate
            from app.schemas.task import TaskPriority, TaskStatus

            t_create = SchemaTaskCreate(
                title=cast(str, t_data["title"]),
                description=cast(str, t_data["description"]),
                status=TaskStatus(cast(str, t_data["status"])),
                priority=TaskPriority(cast(str, t_data["priority"])),
                assignee_id=cast(Optional[int], t_data["assignee_id"]),
                due_date=cast(datetime.date, t_data["due_date"]),
                story_points=cast(int, t_data["story_points"]),
                estimated_hours=cast(int, t_data["estimated_hours"]),
                tags=cast(List[str], t_data["tags"]),
            )
            new_task = TaskService.create_task(
                db,
                cast(int, t_data["project_id"]),
                t_create,
                current_user.id,
                commit=False,
            )
            created_tasks.append(new_task)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kesalahan internal saat menyimpan ke database: {str(e)}",
        )

    return {
        "message": f"Berhasil mengimpor {len(created_tasks)} task.",
        "count": len(created_tasks),
    }


# ── GET /tasks/{id} ───────────────────────────────────────────────────────────


@router.get("/{task_id}", summary="Get task by ID")
def get_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    task = TaskRepository.get_by_id(db, task_id)
    if task is None:
        raise NotFoundException("Task", task_id)

    # Project authorization
    check_project_access(db, current_user, task.project_id, min_role="VIEWER")
    return task


# ── POST /tasks ───────────────────────────────────────────────────────────────


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
def create_task(
    task_in: TaskCreate,
    project_id: int,  # Pass project_id as query param or require it in payload
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    # Project authorization: must be member of project
    check_project_access(db, current_user, project_id, min_role="MEMBER")
    return TaskService.create_task(db, project_id, task_in, current_user.id)


# ── PUT /tasks/{id} ───────────────────────────────────────────────────────────


@router.put("/{task_id}", summary="Update a task")
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    task = TaskRepository.get_by_id(db, task_id)
    if task is None:
        raise NotFoundException("Task", task_id)

    # Project authorization: must be member of project
    check_project_access(db, current_user, task.project_id, min_role="MEMBER")
    return TaskService.update_task(db, task, task_in, current_user.id)


# ── DELETE /tasks/{id} ────────────────────────────────────────────────────────


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
)
def delete_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    task = TaskRepository.get_by_id(db, task_id)
    if task is None:
        raise NotFoundException("Task", task_id)

    # Project authorization: must be member/owner of project
    check_project_access(db, current_user, task.project_id, min_role="MEMBER")
    TaskService.soft_delete_task(db, task, current_user.id)
    return None

