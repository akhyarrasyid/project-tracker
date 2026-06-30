import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from sqlalchemy import func

import app.db.models  # noqa: F401
from app.db.base import Base
from app.db.models.activity_log import ActivityLog
from app.db.models.project import Project
from app.db.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.task_service import TaskService
from tests.conftest import TestingSessionLocal, engine, seed_test_hierarchy


def test_task_service_transitions(db_session):
    seed = seed_test_hierarchy(db_session)
    task = Task(
        title="Service Task",
        description="Desc",
        status="Todo",
        project_id=seed["project_id"],
        created_by_id=seed["admin"].id,
        due_date=datetime.date.today(),
        story_points=3,
        estimated_hours=4,
        actual_hours=0,
        progress_percentage=0,
    )
    db_session.add(task)
    db_session.commit()

    # Same status -> no-op
    TaskService.validate_and_apply_status_transition(
        db_session, task, "Todo", seed["admin"].id
    )

    # Todo -> In Progress -> OK
    TaskService.validate_and_apply_status_transition(
        db_session, task, "In Progress", seed["admin"].id
    )

    # In Progress -> Review -> OK
    task.status = "In Progress"
    db_session.commit()
    TaskService.validate_and_apply_status_transition(
        db_session, task, "Review", seed["admin"].id
    )

    # Invalid main transition: In Progress -> Done
    task.status = "In Progress"
    db_session.commit()
    with pytest.raises(HTTPException) as exc:
        TaskService.validate_and_apply_status_transition(
            db_session, task, "Done", seed["admin"].id
        )
    assert exc.value.status_code == 400
    assert "Invalid status transition" in exc.value.detail


def test_task_service_progress_sync_done(db_session):
    seed = seed_test_hierarchy(db_session)

    # Creation with Done status
    task_in = TaskCreate(
        title="Done Task Creation",
        description="Desc",
        status="Done",
        due_date=datetime.date.today(),
        story_points=3,
        estimated_hours=4,
    )
    task = TaskService.create_task(
        db_session, seed["project_id"], task_in, seed["admin"].id
    )
    assert task.progress_percentage == 100
    assert task.completed_at is not None
    assert task.completed_by_id == seed["admin"].id

    # Update with Done status
    task2 = Task(
        title="Progress Task",
        description="Desc",
        status="Todo",
        project_id=seed["project_id"],
        created_by_id=seed["admin"].id,
        due_date=datetime.date.today(),
        story_points=3,
        estimated_hours=4,
        actual_hours=0,
        progress_percentage=0,
    )
    db_session.add(task2)
    db_session.commit()

    task_update = TaskUpdate(status="Done")
    # Bypass transition validations via admin or manual transition
    TaskService.update_task(db_session, task2, task_update, seed["admin"].id)
    assert task2.progress_percentage == 100
    assert task2.completed_at is not None
    assert task2.completed_by_id == seed["admin"].id


def test_task_service_progress_sync_create_and_update_cases(db_session):
    seed = seed_test_hierarchy(db_session)

    # 1. Create with progress=100 -> auto status Done
    task_in1 = TaskCreate(
        title="100% Progress Task",
        description="Desc",
        status="Todo",
        due_date=datetime.date.today(),
        story_points=3,
        estimated_hours=4,
        progress_percentage=100,
    )
    t1 = TaskService.create_task(
        db_session, seed["project_id"], task_in1, seed["admin"].id
    )
    assert t1.status == "Done"

    # 2. Create with progress=50 -> auto status In Progress
    task_in2 = TaskCreate(
        title="50% Progress Task",
        description="Desc",
        status="Todo",
        due_date=datetime.date.today(),
        story_points=3,
        estimated_hours=4,
        progress_percentage=50,
    )
    t2 = TaskService.create_task(
        db_session, seed["project_id"], task_in2, seed["admin"].id
    )
    assert t2.status == "In Progress"

    # 3. Update with progress=100 -> auto status Done
    task_up1 = TaskUpdate(progress_percentage=100)
    TaskService.update_task(db_session, t2, task_up1, seed["admin"].id)
    assert t2.status == "Done"

    # 4. Update with progress=50 -> auto status In Progress (if currently Todo/Done)
    t2.status = "Todo"
    t2.progress_percentage = 0
    db_session.commit()
    task_up2 = TaskUpdate(progress_percentage=50)
    TaskService.update_task(db_session, t2, task_up2, seed["admin"].id)
    assert t2.status == "In Progress"

    # 5. Update assignee -> activity log
    task_up3 = TaskUpdate(assignee_id=seed["worker"].id)
    TaskService.update_task(db_session, t2, task_up3, seed["admin"].id)
    # Check if there is an ActivityLog for assignee change
    log = (
        db_session.query(ActivityLog)
        .filter(ActivityLog.task_id == t2.id, ActivityLog.field == "assignee_id")
        .first()
    )
    assert log is not None
    assert log.new_value == str(seed["worker"].id)


def test_task_service_logs_blocked_flag_changes(db_session):
    seed = seed_test_hierarchy(db_session)
    task = TaskService.create_task(
        db_session,
        seed["project_id"],
        TaskCreate(
            title="Blocked flag",
            description="Desc",
            due_date=datetime.date.today(),
            story_points=3,
            estimated_hours=4,
        ),
        seed["admin"].id,
    )

    TaskService.update_task(
        db_session,
        task,
        TaskUpdate(is_blocked=True, blocked_reason="Waiting for vendor"),
        seed["admin"].id,
    )

    logs = (
        db_session.query(ActivityLog)
        .filter(ActivityLog.task_id == task.id, ActivityLog.field.in_(["is_blocked", "blocked_reason"]))
        .all()
    )
    fields = {log.field for log in logs}
    assert fields == {"is_blocked", "blocked_reason"}


def test_create_task_allocates_unique_issue_numbers_concurrently():
    assert engine.dialect.name == "postgresql"
    Base.metadata.create_all(bind=engine)

    setup_session = TestingSessionLocal()
    seed = seed_test_hierarchy(setup_session)
    setup_session.commit()
    project_id = seed["project_id"]
    creator_id = seed["admin"].id
    setup_session.close()

    barrier = threading.Barrier(6)
    results: list[tuple[int, int, str | None]] = []

    def create_issue(index: int) -> tuple[int, int, str | None]:
        session = TestingSessionLocal()
        try:
            barrier.wait(timeout=5)
            task = TaskService.create_task(
                session,
                project_id,
                TaskCreate(
                    title=f"Concurrent {index}",
                    description="Parallel create",
                    due_date=datetime.date.today(),
                    story_points=3,
                    estimated_hours=4,
                ),
                creator_id,
            )
            return task.id, task.number, task.key
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(create_issue, range(6)))

    verify_session = TestingSessionLocal()
    try:
        project = verify_session.query(Project).filter(Project.id == project_id).one()
        task_numbers = sorted(number for _, number, _ in results)
        stored_numbers = sorted(
            number
            for (number,) in verify_session.query(Task.number)
            .filter(Task.project_id == project_id)
            .all()
        )
        assert task_numbers == [1, 2, 3, 4, 5, 6]
        assert stored_numbers == [1, 2, 3, 4, 5, 6]
        assert len({key for _, _, key in results}) == 6
        assert project.issue_sequence == 6
        assert (
            verify_session.query(func.count(Task.id))
            .filter(Task.project_id == project_id)
            .scalar()
            == 6
        )
    finally:
        verify_session.close()


def test_move_task_reorders_within_column_and_rebalances_when_gap_is_exhausted(db_session):
    seed = seed_test_hierarchy(db_session)
    top = TaskService.create_task(
        db_session,
        seed["project_id"],
        TaskCreate(
            title="Top",
            description="Top",
            status="Todo",
            due_date=datetime.date.today(),
            story_points=3,
            estimated_hours=4,
        ),
        seed["admin"].id,
    )
    bottom = TaskService.create_task(
        db_session,
        seed["project_id"],
        TaskCreate(
            title="Bottom",
            description="Bottom",
            status="Todo",
            due_date=datetime.date.today(),
            story_points=3,
            estimated_hours=4,
        ),
        seed["admin"].id,
    )
    moving = TaskService.create_task(
        db_session,
        seed["project_id"],
        TaskCreate(
            title="Moving",
            description="Moving",
            status="Review",
            due_date=datetime.date.today(),
            story_points=3,
            estimated_hours=4,
        ),
        seed["admin"].id,
    )

    top.rank = 1
    bottom.rank = 2
    db_session.commit()

    moved = TaskService.move_task(
        db_session,
        task_id=moving.id,
        target_status="Todo",
        actor_id=seed["admin"].id,
        before_issue_id=bottom.id,
        after_issue_id=top.id,
    )

    ordered = (
        db_session.query(Task)
        .filter(Task.project_id == seed["project_id"], Task.status == "Todo")
        .order_by(Task.rank.asc(), Task.id.asc())
        .all()
    )
    ordered_subset = [task for task in ordered if task.id in {top.id, moving.id, bottom.id}]
    assert moved.status == "Todo"
    assert [task.id for task in ordered_subset] == [top.id, moving.id, bottom.id]
    assert [task.rank for task in ordered_subset] == [1024, 1536, 2048]


def test_move_task_to_top_of_column_assigns_rank_before_first_issue(db_session):
    seed = seed_test_hierarchy(db_session)
    first = TaskService.create_task(
        db_session,
        seed["project_id"],
        TaskCreate(
            title="First",
            description="First",
            status="Todo",
            due_date=datetime.date.today(),
            story_points=3,
            estimated_hours=4,
        ),
        seed["admin"].id,
    )
    moving = TaskService.create_task(
        db_session,
        seed["project_id"],
        TaskCreate(
            title="Moving first",
            description="Move",
            status="Review",
            due_date=datetime.date.today(),
            story_points=3,
            estimated_hours=4,
        ),
        seed["admin"].id,
    )

    moved = TaskService.move_task(
        db_session,
        task_id=moving.id,
        target_status="Todo",
        actor_id=seed["admin"].id,
        before_issue_id=first.id,
    )
    assert moved.rank < first.rank
    assert moved.status == "Todo"
