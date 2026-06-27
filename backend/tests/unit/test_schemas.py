"""Unit tests for TaskCreate and TaskUpdate schema validation."""
import datetime
import pytest
from pydantic import ValidationError

from app.schemas.task import TaskCreate, TaskUpdate, TaskStatus, TaskPriority


# ── Minimal valid payload ──────────────────────────────────────────────────────

BASE = {
    "title": "Test Task",
    "description": "A test task.",
    "status": "Todo",
    "priority": "Medium",
    "department": "Engineering",
    "team": "Backend",
    "assignee": "Alice",
    "created_by": "admin",
    "due_date": "2025-12-31",
    "story_points": 3,
    "estimated_hours": 8,
    "sprint": "Sprint-1",
    "quarter": "Q1",
    "risk_level": "Low",
    "customer_impact": "None",
    "sla_hours": 48,
}


def make(**overrides):
    data = {**BASE, **overrides}
    return TaskCreate(**data)


class TestTaskCreateTitle:
    def test_valid_title(self):
        t = make(title="Valid Title")
        assert t.title == "Valid Title"

    def test_title_is_stripped(self):
        t = make(title="  padded  ")
        assert t.title == "padded"

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            make(title="")

    def test_whitespace_only_title_raises(self):
        with pytest.raises(ValidationError):
            make(title="   ")

    def test_title_255_chars_ok(self):
        t = make(title="x" * 255)
        assert len(t.title) == 255

    def test_title_256_chars_raises(self):
        with pytest.raises(ValidationError):
            make(title="x" * 256)

    def test_missing_title_raises(self):
        with pytest.raises(ValidationError):
            data = {k: v for k, v in BASE.items() if k != "title"}
            TaskCreate(**data)


class TestTaskCreateStatus:
    def test_valid_status_todo(self):
        t = make(status="Todo")
        assert t.status == TaskStatus.TODO

    def test_valid_status_in_progress(self):
        t = make(status="In Progress")
        assert t.status == TaskStatus.IN_PROGRESS

    def test_valid_status_review(self):
        t = make(status="Review")
        assert t.status == TaskStatus.REVIEW

    def test_valid_status_blocked(self):
        t = make(status="Blocked")
        assert t.status == TaskStatus.BLOCKED

    def test_valid_status_done(self):
        t = make(status="Done")
        assert t.status == TaskStatus.DONE

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            make(status="Selesai")

    def test_lowercase_status_raises(self):
        with pytest.raises(ValidationError):
            make(status="todo")


class TestTaskCreatePriority:
    def test_all_valid_priorities(self):
        for p in ("Low", "Medium", "High", "Critical"):
            t = make(priority=p)
            assert t.priority.value == p

    def test_invalid_priority_raises(self):
        with pytest.raises(ValidationError):
            make(priority="Urgent")


class TestTaskCreateStoryPoints:
    def test_valid_fibonacci(self):
        for sp in (1, 2, 3, 5, 8, 13):
            t = make(story_points=sp)
            assert t.story_points == sp

    def test_invalid_story_points_raises(self):
        with pytest.raises(ValidationError):
            make(story_points=4)

    def test_zero_story_points_raises(self):
        with pytest.raises(ValidationError):
            make(story_points=0)


class TestTaskCreateSlaHours:
    def test_valid_sla_tiers(self):
        for sla in (24, 48, 72, 120):
            t = make(sla_hours=sla)
            assert t.sla_hours == sla

    def test_invalid_sla_raises(self):
        with pytest.raises(ValidationError):
            make(sla_hours=36)


class TestTaskCreateProgressPercentage:
    def test_zero_is_valid(self):
        t = make(progress_percentage=0)
        assert t.progress_percentage == 0

    def test_100_is_valid(self):
        t = make(progress_percentage=100)
        assert t.progress_percentage == 100

    def test_negative_raises(self):
        with pytest.raises(ValidationError):
            make(progress_percentage=-1)

    def test_over_100_raises(self):
        with pytest.raises(ValidationError):
            make(progress_percentage=101)


class TestTaskCreateTags:
    def test_empty_tags_ok(self):
        t = make(tags=[])
        assert t.tags == []

    def test_four_tags_ok(self):
        t = make(tags=["a", "b", "c", "d"])
        assert len(t.tags) == 4

    def test_five_tags_raises(self):
        with pytest.raises(ValidationError):
            make(tags=["a", "b", "c", "d", "e"])


class TestTaskCreateQuarter:
    def test_all_valid_quarters(self):
        for q in ("Q1", "Q2", "Q3", "Q4"):
            t = make(quarter=q)
            assert t.quarter.value == q

    def test_invalid_quarter_raises(self):
        with pytest.raises(ValidationError):
            make(quarter="Q5")


class TestTaskUpdatePartial:
    def test_empty_update_is_valid(self):
        u = TaskUpdate()
        assert u.title is None
        assert u.status is None

    def test_partial_update_title_only(self):
        u = TaskUpdate(title="New Title")
        assert u.title == "New Title"
        assert u.status is None

    def test_update_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            TaskUpdate(status="Invalid")

    def test_update_empty_title_raises(self):
        with pytest.raises(ValidationError):
            TaskUpdate(title="")

    def test_update_story_points_validation(self):
        with pytest.raises(ValidationError):
            TaskUpdate(story_points=7)

    def test_update_valid_story_points(self):
        u = TaskUpdate(story_points=5)
        assert u.story_points == 5

    def test_update_invalid_sla_hours(self):
        with pytest.raises(ValidationError):
            TaskUpdate(sla_hours=10)

    def test_update_valid_sla_hours(self):
        u = TaskUpdate(sla_hours=24)
        assert u.sla_hours == 24

    def test_update_five_tags_raises(self):
        with pytest.raises(ValidationError):
            TaskUpdate(tags=["a", "b", "c", "d", "e"])

    def test_update_four_tags_ok(self):
        u = TaskUpdate(tags=["a", "b", "c", "d"])
        assert len(u.tags) == 4

