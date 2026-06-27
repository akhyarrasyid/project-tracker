"""E2E tests for POST /api/v1/tasks/ — create task."""
import pytest


class TestCreateTask:

    def test_create_returns_201(self, client, make_task):
        task = make_task()
        assert task["id"] is not None

    def test_create_returns_all_fields(self, client, make_task):
        task = make_task(title="Full Task")
        assert task["title"] == "Full Task"
        assert task["status"] == "Todo"
        assert task["priority"] == "Medium"
        assert "id" in task
        assert "created_at" in task
        assert "updated_at" in task

    def test_create_persists_to_db(self, client, make_task):
        task = make_task(title="Persist Me")
        items = client.get("/api/v1/tasks/").json()["items"]
        assert any(t["id"] == task["id"] for t in items)

    def test_create_all_five_statuses(self, client, make_task):
        for status in ("Todo", "In Progress", "Review", "Blocked", "Done"):
            task = make_task(status=status)
            assert task["status"] == status

    def test_create_all_four_priorities(self, client, make_task):
        for priority in ("Low", "Medium", "High", "Critical"):
            task = make_task(priority=priority)
            assert task["priority"] == priority

    def test_create_fibonacci_story_points(self, client, make_task):
        for sp in (1, 2, 3, 5, 8, 13):
            task = make_task(story_points=sp)
            assert task["story_points"] == sp

    def test_create_invalid_story_points_returns_422(self, client, make_task):
        resp = client.post("/api/v1/tasks/", json={
            **{k: v for k, v in make_task.__self__.__dict__.items() if k != "story_points"},
            "story_points": 4,
        }) if False else None
        # Use conftest payload directly
        from tests.conftest import VALID_TASK_PAYLOAD
        payload = {**VALID_TASK_PAYLOAD, "story_points": 4}
        resp = client.post("/api/v1/tasks/", json=payload)
        assert resp.status_code == 422

    def test_create_missing_title_returns_422(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        payload = {k: v for k, v in VALID_TASK_PAYLOAD.items() if k != "title"}
        resp = client.post("/api/v1/tasks/", json=payload)
        assert resp.status_code == 422

    def test_create_empty_title_returns_422(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        resp = client.post("/api/v1/tasks/", json={**VALID_TASK_PAYLOAD, "title": ""})
        assert resp.status_code == 422

    def test_create_title_too_long_returns_422(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        resp = client.post("/api/v1/tasks/", json={**VALID_TASK_PAYLOAD, "title": "x" * 256})
        assert resp.status_code == 422

    def test_create_invalid_status_returns_422(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        resp = client.post("/api/v1/tasks/", json={**VALID_TASK_PAYLOAD, "status": "InvalidStatus"})
        assert resp.status_code == 422

    def test_create_invalid_sla_hours_returns_422(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        resp = client.post("/api/v1/tasks/", json={**VALID_TASK_PAYLOAD, "sla_hours": 36})
        assert resp.status_code == 422

    def test_create_tags_stored_correctly(self, client, make_task):
        task = make_task(tags=["backend", "api", "v2"])
        assert task["tags"] == ["backend", "api", "v2"]

    def test_create_dependencies_stored_correctly(self, client, make_task):
        task = make_task(dependencies=[1, 2, 3])
        assert task["dependencies"] == [1, 2, 3]

    def test_create_assigns_unique_ids(self, client, make_task):
        ids = [make_task(title=f"T{i}")["id"] for i in range(5)]
        assert len(set(ids)) == 5

    def test_create_extra_fields_ignored(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        payload = {**VALID_TASK_PAYLOAD, "hacker_field": "DROP TABLE tasks;"}
        resp = client.post("/api/v1/tasks/", json=payload)
        assert resp.status_code == 201
        assert "hacker_field" not in resp.json()

    def test_create_unicode_title(self, client, make_task):
        task = make_task(title="タスク 🎯 مهمة")
        assert task["title"] == "タスク 🎯 مهمة"

    def test_create_sql_injection_title_stored_safely(self, client, make_task):
        sqli = "'; DROP TABLE tasks; --"
        task = make_task(title=sqli)
        assert task["title"] == sqli
