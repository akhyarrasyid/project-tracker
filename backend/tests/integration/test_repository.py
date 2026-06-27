"""Integration tests for TaskRepository — CRUD, pagination, filtering, sorting, search."""
import datetime
import pytest

from app.db.models.task import Task
from app.db.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate

# ── Minimal valid TaskCreate data ─────────────────────────────────────────────

BASE = {
    "title": "Repo Task",
    "description": "Test.",
    "status": "Todo",
    "priority": "Medium",
    "department": "Engineering",
    "team": "Backend",
    "assignee": "Alice",
    "created_by": "admin",
    "due_date": datetime.date(2025, 12, 31),
    "story_points": 3,
    "estimated_hours": 8,
    "sprint": "Sprint-1",
    "quarter": "Q1",
    "risk_level": "Low",
    "customer_impact": "None",
    "sla_hours": 48,
}


def create(db, **overrides):
    data = {**BASE, **overrides}
    return TaskRepository.create(db, TaskCreate(**data))


class TestRepositoryCreate:
    def test_create_returns_task(self, db_session):
        task = create(db_session)
        assert task.id is not None
        assert task.title == "Repo Task"

    def test_create_persists(self, db_session):
        task = create(db_session, title="Persist Me")
        fetched = TaskRepository.get_by_id(db_session, task.id)
        assert fetched is not None
        assert fetched.title == "Persist Me"

    def test_create_assigns_unique_ids(self, db_session):
        t1 = create(db_session, title="T1")
        t2 = create(db_session, title="T2")
        assert t1.id != t2.id

    def test_create_sets_default_status(self, db_session):
        task = create(db_session)
        assert task.status == "Todo"

    def test_create_sets_created_at(self, db_session):
        task = create(db_session)
        assert task.created_at is not None


class TestRepositoryGetById:
    def test_get_existing_task(self, db_session):
        task = create(db_session)
        found = TaskRepository.get_by_id(db_session, task.id)
        assert found.id == task.id

    def test_get_nonexistent_returns_none(self, db_session):
        result = TaskRepository.get_by_id(db_session, 99999)
        assert result is None


class TestRepositoryUpdate:
    def test_update_title(self, db_session):
        task = create(db_session, title="Before")
        updated = TaskRepository.update(db_session, task, TaskUpdate(title="After"))
        assert updated.title == "After"

    def test_update_status(self, db_session):
        task = create(db_session, status="Todo")
        updated = TaskRepository.update(db_session, task, TaskUpdate(status="Done"))
        assert updated.status == "Done"

    def test_partial_update_leaves_other_fields(self, db_session):
        task = create(db_session, title="Keep Me", status="Todo")
        TaskRepository.update(db_session, task, TaskUpdate(status="In Progress"))
        assert task.title == "Keep Me"

    def test_empty_update_changes_nothing(self, db_session):
        task = create(db_session, title="Stable")
        TaskRepository.update(db_session, task, TaskUpdate())
        assert task.title == "Stable"


class TestRepositoryDelete:
    def test_delete_removes_task(self, db_session):
        task = create(db_session)
        TaskRepository.delete(db_session, task)
        assert TaskRepository.get_by_id(db_session, task.id) is None

    def test_delete_does_not_affect_others(self, db_session):
        t1 = create(db_session, title="Keep")
        t2 = create(db_session, title="Delete")
        TaskRepository.delete(db_session, t2)
        assert TaskRepository.get_by_id(db_session, t1.id) is not None


class TestRepositoryListPagination:
    def test_returns_tuple(self, db_session):
        result = TaskRepository.list(db_session)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_empty_db_returns_zero_total(self, db_session):
        _, total = TaskRepository.list(db_session)
        assert total == 0

    def test_total_matches_inserted(self, db_session):
        for i in range(5):
            create(db_session, title=f"Task {i}")
        _, total = TaskRepository.list(db_session)
        assert total == 5

    def test_page_size_limits_results(self, db_session):
        for i in range(10):
            create(db_session, title=f"Task {i}")
        items, total = TaskRepository.list(db_session, page=1, size=3)
        assert len(items) == 3
        assert total == 10

    def test_second_page_returns_next_batch(self, db_session):
        for i in range(10):
            create(db_session, title=f"Task {i}")
        p1, _ = TaskRepository.list(db_session, page=1, size=5, sort_by="id", sort_order="asc")
        p2, _ = TaskRepository.list(db_session, page=2, size=5, sort_by="id", sort_order="asc")
        ids1 = {t.id for t in p1}
        ids2 = {t.id for t in p2}
        assert not ids1.intersection(ids2)

    def test_beyond_last_page_returns_empty(self, db_session):
        create(db_session)
        items, _ = TaskRepository.list(db_session, page=999, size=20)
        assert items == []


class TestRepositoryListFiltering:
    def test_filter_by_status(self, db_session):
        create(db_session, title="Todo", status="Todo")
        create(db_session, title="Done", status="Done")
        items, total = TaskRepository.list(db_session, status="Todo")
        assert total == 1
        assert items[0].status == "Todo"

    def test_filter_by_priority(self, db_session):
        create(db_session, priority="High")
        create(db_session, priority="Low")
        items, total = TaskRepository.list(db_session, priority="High")
        assert total == 1
        assert items[0].priority == "High"

    def test_filter_by_department(self, db_session):
        create(db_session, department="Engineering")
        create(db_session, department="Marketing")
        items, _ = TaskRepository.list(db_session, department="Marketing")
        assert len(items) == 1

    def test_filter_by_assignee(self, db_session):
        create(db_session, assignee="Alice")
        create(db_session, assignee="Bob")
        items, _ = TaskRepository.list(db_session, assignee="Alice")
        assert items[0].assignee == "Alice"

    def test_comma_separated_status(self, db_session):
        create(db_session, status="Todo")
        create(db_session, status="Done")
        create(db_session, status="Review")
        items, total = TaskRepository.list(db_session, status="Todo,Done")
        assert total == 2

    def test_filter_by_team(self, db_session):
        create(db_session, team="Frontend")
        create(db_session, team="Backend")
        items, _ = TaskRepository.list(db_session, team="Frontend")
        assert len(items) == 1
        assert items[0].team == "Frontend"

    def test_filter_by_sprint(self, db_session):
        create(db_session, sprint="Sprint-1")
        create(db_session, sprint="Sprint-2")
        items, _ = TaskRepository.list(db_session, sprint="Sprint-1")
        assert len(items) == 1
        assert items[0].sprint == "Sprint-1"

    def test_filter_by_quarter(self, db_session):
        create(db_session, quarter="Q1")
        create(db_session, quarter="Q2")
        items, _ = TaskRepository.list(db_session, quarter="Q1")
        assert len(items) == 1
        assert items[0].quarter == "Q1"

    def test_filter_by_risk_level(self, db_session):
        create(db_session, risk_level="High")
        create(db_session, risk_level="Low")
        items, _ = TaskRepository.list(db_session, risk_level="High")
        assert len(items) == 1
        assert items[0].risk_level == "High"



class TestRepositoryListSearch:
    def test_search_by_title(self, db_session):
        create(db_session, title="Launch Campaign")
        create(db_session, title="Fix Bug")
        items, _ = TaskRepository.list(db_session, search="campaign")
        assert len(items) == 1
        assert "Campaign" in items[0].title

    def test_search_by_description(self, db_session):
        create(db_session, title="Task A", description="unique_keyword_xyz")
        create(db_session, title="Task B", description="nothing special")
        items, _ = TaskRepository.list(db_session, search="unique_keyword_xyz")
        assert len(items) == 1

    def test_search_no_match_returns_empty(self, db_session):
        create(db_session, title="Something")
        items, total = TaskRepository.list(db_session, search="zzznomatch")
        assert total == 0


class TestRepositoryListSorting:
    def test_sort_by_id_asc(self, db_session):
        for i in range(3):
            create(db_session, title=f"Task {i}")
        items, _ = TaskRepository.list(db_session, sort_by="id", sort_order="asc")
        ids = [t.id for t in items]
        assert ids == sorted(ids)

    def test_sort_by_id_desc(self, db_session):
        for i in range(3):
            create(db_session, title=f"Task {i}")
        items, _ = TaskRepository.list(db_session, sort_by="id", sort_order="desc")
        ids = [t.id for t in items]
        assert ids == sorted(ids, reverse=True)


class TestRepositoryBulk:
    def test_bulk_create(self, db_session):
        data = [
            {**BASE, "title": "Bulk 1"},
            {**BASE, "title": "Bulk 2"},
        ]
        count = TaskRepository.bulk_create(db_session, data)
        assert count == 2
        assert db_session.query(Task).filter(Task.title.like("Bulk %")).count() == 2

