import datetime

import pytest
from fastapi import HTTPException

from app.db.models.activity_log import ActivityLog
from app.db.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.task_service import TaskService
from tests.conftest import seed_test_hierarchy


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

    # In Progress -> Blocked -> OK
    task.status = "In Progress"
    db_session.commit()
    # Log status change in activity log so we have a record
    log = ActivityLog(
        task_id=task.id,
        actor_id=seed["admin"].id,
        action="update",
        field="status",
        old_value="Todo",
        new_value="In Progress",
    )
    db_session.add(log)
    db_session.commit()

    # Apply transition to Blocked
    TaskService.validate_and_apply_status_transition(
        db_session, task, "Blocked", seed["admin"].id
    )

    # Set status to Blocked in DB
    task.status = "Blocked"
    db_session.commit()

    # Blocked -> back to In Progress -> OK
    TaskService.validate_and_apply_status_transition(
        db_session, task, "In Progress", seed["admin"].id
    )

    # Blocked -> Todo -> Fails because previous was In Progress
    with pytest.raises(HTTPException) as exc:
        TaskService.validate_and_apply_status_transition(
            db_session, task, "Todo", seed["admin"].id
        )
    assert exc.value.status_code == 400
    assert "Must return to previous state" in exc.value.detail

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


def test_get_last_non_blocked_status_no_log(db_session):
    val = TaskService.get_last_non_blocked_status(db_session, 99999)
    assert val == "Todo"
