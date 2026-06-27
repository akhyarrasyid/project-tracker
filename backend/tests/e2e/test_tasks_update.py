"""E2E tests for PUT /api/v1/tasks/{id} — update task."""
import time
import pytest


class TestUpdateTask:

    def test_update_returns_200(self, client, make_task):
        task = make_task()
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": "Updated"})
        assert resp.status_code == 200

    def test_update_title(self, client, make_task):
        task = make_task(title="Old")
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": "New"})
        assert resp.json()["title"] == "New"

    def test_update_status(self, client, make_task):
        task = make_task(status="Todo")
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"status": "In Progress"})
        assert resp.json()["status"] == "In Progress"

    def test_update_priority(self, client, make_task):
        task = make_task(priority="Low")
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"priority": "Critical"})
        assert resp.json()["priority"] == "Critical"

    def test_update_progress_percentage(self, client, make_task):
        task = make_task()
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"progress_percentage": 75})
        assert resp.json()["progress_percentage"] == 75

    def test_partial_update_leaves_other_fields(self, client, make_task):
        task = make_task(title="Original", status="Todo")
        client.put(f"/api/v1/tasks/{task['id']}", json={"status": "Done"})
        updated = client.get(f"/api/v1/tasks/{task['id']}").json()
        assert updated["title"] == "Original"
        assert updated["status"] == "Done"

    def test_update_bumps_updated_at(self, client, make_task):
        task = make_task()
        original = task["updated_at"]
        time.sleep(0.05)
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": "Changed"})
        assert resp.json()["updated_at"] != original

    def test_update_does_not_change_created_at(self, client, make_task):
        task = make_task()
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": "Changed"})
        assert resp.json()["created_at"] == task["created_at"]

    def test_update_does_not_change_id(self, client, make_task):
        task = make_task()
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": "Changed"})
        assert resp.json()["id"] == task["id"]

    def test_update_empty_body_no_change(self, client, make_task):
        task = make_task(title="Stable")
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Stable"

    def test_update_one_task_does_not_affect_another(self, client, make_task):
        t1 = make_task(title="Task One")
        t2 = make_task(title="Task Two")
        client.put(f"/api/v1/tasks/{t1['id']}", json={"title": "Task One Updated"})
        other = client.get(f"/api/v1/tasks/{t2['id']}").json()
        assert other["title"] == "Task Two"

    # ── Not found ─────────────────────────────────────────────────────────────

    def test_update_nonexistent_returns_404(self, client):
        resp = client.put("/api/v1/tasks/99999", json={"title": "Ghost"})
        assert resp.status_code == 404

    def test_update_404_has_detail_key(self, client):
        resp = client.put("/api/v1/tasks/99999", json={"title": "Ghost"})
        assert "detail" in resp.json()

    # ── Validation ────────────────────────────────────────────────────────────

    def test_update_empty_title_returns_422(self, client, make_task):
        task = make_task()
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": ""})
        assert resp.status_code == 422

    def test_update_title_too_long_returns_422(self, client, make_task):
        task = make_task()
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": "x" * 256})
        assert resp.status_code == 422

    def test_update_invalid_status_returns_422(self, client, make_task):
        task = make_task()
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"status": "Selesai"})
        assert resp.status_code == 422

    def test_update_invalid_story_points_returns_422(self, client, make_task):
        task = make_task()
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"story_points": 7})
        assert resp.status_code == 422

    # ── ID edge cases ─────────────────────────────────────────────────────────

    def test_update_string_id_returns_422(self, client):
        resp = client.put("/api/v1/tasks/abc", json={"title": "x"})
        assert resp.status_code == 422

    def test_update_id_in_body_is_ignored(self, client, make_task):
        task = make_task()
        original_id = task["id"]
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"id": 9999, "title": "Sneaky"})
        assert resp.json()["id"] == original_id
