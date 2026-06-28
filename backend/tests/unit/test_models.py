"""Unit tests for Task SQLAlchemy model — defaults, nullability, constraints."""

import datetime

from app.db.models.task import Task
from tests.conftest import seed_test_hierarchy


class TestTaskModelDefaults:
    def test_status_defaults_to_todo(self, db_session):
        seed = seed_test_hierarchy(db_session)
        task = Task(
            title="Test",
            description="Desc",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            assignee_id=seed["worker"].id,
            due_date=datetime.date(2025, 12, 31),
            story_points=3,
            estimated_hours=8,
            quarter="Q1",
            risk_level="Low",
            customer_impact="None",
            sla_hours=48,
        )
        db_session.add(task)
        db_session.commit()
        assert task.status == "Todo"

    def test_priority_defaults_to_medium(self, db_session):
        seed = seed_test_hierarchy(db_session)
        task = Task(
            title="Test",
            description="Desc",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            assignee_id=seed["worker"].id,
            due_date=datetime.date(2025, 12, 31),
            story_points=3,
            estimated_hours=8,
            quarter="Q1",
            risk_level="Low",
            customer_impact="None",
            sla_hours=48,
        )
        db_session.add(task)
        db_session.commit()
        assert task.priority == "Medium"

    def test_progress_percentage_defaults_to_zero(self, db_session):
        seed = seed_test_hierarchy(db_session)
        task = Task(
            title="Test",
            description="Desc",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            assignee_id=seed["worker"].id,
            due_date=datetime.date(2025, 12, 31),
            story_points=3,
            estimated_hours=8,
            quarter="Q1",
            risk_level="Low",
            customer_impact="None",
            sla_hours=48,
        )
        db_session.add(task)
        db_session.commit()
        assert task.progress_percentage == 0

    def test_completed_at_is_nullable(self, db_session):
        seed = seed_test_hierarchy(db_session)
        task = Task(
            title="Test",
            description="Desc",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            assignee_id=seed["worker"].id,
            due_date=datetime.date(2025, 12, 31),
            story_points=3,
            estimated_hours=8,
            quarter="Q1",
            risk_level="Low",
            customer_impact="None",
            sla_hours=48,
        )
        db_session.add(task)
        db_session.commit()
        assert task.completed_at is None

    def test_dependencies_defaults_to_empty_list(self, db_session):
        seed = seed_test_hierarchy(db_session)
        task = Task(
            title="Test",
            description="Desc",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            assignee_id=seed["worker"].id,
            due_date=datetime.date(2025, 12, 31),
            story_points=3,
            estimated_hours=8,
            quarter="Q1",
            risk_level="Low",
            customer_impact="None",
            sla_hours=48,
        )
        db_session.add(task)
        db_session.commit()
        assert task.dependencies == []

    def test_tags_defaults_to_empty_list(self, db_session):
        seed = seed_test_hierarchy(db_session)
        task = Task(
            title="Test",
            description="Desc",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            assignee_id=seed["worker"].id,
            due_date=datetime.date(2025, 12, 31),
            story_points=3,
            estimated_hours=8,
            quarter="Q1",
            risk_level="Low",
            customer_impact="None",
            sla_hours=48,
        )
        db_session.add(task)
        db_session.commit()
        assert task.tags == []

    def test_created_at_is_auto_set(self, db_session):
        seed = seed_test_hierarchy(db_session)
        task = Task(
            title="Test",
            description="Desc",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            assignee_id=seed["worker"].id,
            due_date=datetime.date(2025, 12, 31),
            story_points=3,
            estimated_hours=8,
            quarter="Q1",
            risk_level="Low",
            customer_impact="None",
            sla_hours=48,
        )
        db_session.add(task)
        db_session.commit()
        assert task.created_at is not None

    def test_id_autoincrement(self, db_session):
        seed = seed_test_hierarchy(db_session)
        t1 = Task(
            title="T1",
            description="D",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            assignee_id=seed["worker"].id,
            due_date=datetime.date(2025, 12, 31),
            story_points=1,
            estimated_hours=1,
            quarter="Q1",
            risk_level="Low",
            customer_impact="None",
            sla_hours=24,
        )
        t2 = Task(
            title="T2",
            description="D",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            assignee_id=seed["worker"].id,
            due_date=datetime.date(2025, 12, 31),
            story_points=1,
            estimated_hours=1,
            quarter="Q1",
            risk_level="Low",
            customer_impact="None",
            sla_hours=24,
        )
        db_session.add_all([t1, t2])
        db_session.commit()
        assert t1.id != t2.id
        assert isinstance(t1.id, int)

    def test_json_fields_persist_correctly(self, db_session):
        seed = seed_test_hierarchy(db_session)
        task = Task(
            title="JSON Test",
            description="D",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            assignee_id=seed["worker"].id,
            due_date=datetime.date(2025, 12, 31),
            story_points=2,
            estimated_hours=4,
            quarter="Q2",
            risk_level="Medium",
            customer_impact="Low",
            sla_hours=72,
            dependencies=[1, 2, 3],
            tags=["backend", "api"],
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        assert task.dependencies == [1, 2, 3]
        assert task.tags == ["backend", "api"]
