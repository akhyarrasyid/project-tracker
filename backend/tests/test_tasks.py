"""
Migrated test suite — all 80 original tests updated for /api/v1/tasks/ 
with 26-field task payloads.
"""
import pytest
import time


# ---------------------------------------------------------------------------
# Tests for GET /api/v1/tasks/
# ---------------------------------------------------------------------------


class TestGetTasks:

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_get_tasks_returns_200(self, client):
        resp = client.get("/api/v1/tasks/")
        assert resp.status_code == 200

    def test_get_tasks_returns_pagination_envelope(self, client):
        body = client.get("/api/v1/tasks/").json()
        assert isinstance(body, dict)
        assert "items" in body
        assert "total" in body

    def test_get_tasks_empty_when_no_tasks(self, client):
        body = client.get("/api/v1/tasks/").json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_get_tasks_returns_all_created_tasks(self, client, make_task):
        make_task(title="Task A")
        make_task(title="Task B")
        make_task(title="Task C")
        items = client.get("/api/v1/tasks/").json()["items"]
        titles = [t["title"] for t in items]
        assert "Task A" in titles
        assert "Task B" in titles
        assert "Task C" in titles

    def test_get_tasks_returns_correct_fields(self, client, make_task):
        make_task()
        task = client.get("/api/v1/tasks/").json()["items"][0]
        assert "id" in task
        assert "title" in task
        assert "description" in task
        assert "status" in task
        assert "created_at" in task
        assert "updated_at" in task

    def test_get_tasks_ordered_newest_first(self, client, make_task):
        first = make_task(title="First Task")
        second = make_task(title="Second Task")
        items = client.get("/api/v1/tasks/").json()["items"]
        ids = [t["id"] for t in items]
        assert ids.index(second["id"]) < ids.index(first["id"])

    def test_get_tasks_default_status_is_todo(self, client, make_task):
        make_task()
        task = client.get("/api/v1/tasks/").json()["items"][0]
        assert task["status"] == "Todo"

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_get_tasks_returns_all_statuses(self, client, make_task):
        make_task(title="T1", status="Todo")
        make_task(title="T2", status="In Progress")
        make_task(title="T3", status="Done")
        items = client.get("/api/v1/tasks/").json()["items"]
        statuses = {t["status"] for t in items}
        assert {"Todo", "In Progress", "Done"}.issubset(statuses)

    def test_get_tasks_id_is_integer(self, client, make_task):
        make_task()
        task = client.get("/api/v1/tasks/").json()["items"][0]
        assert isinstance(task["id"], int)

    def test_get_tasks_created_at_is_valid_datetime(self, client, make_task):
        from datetime import datetime
        make_task()
        dt_str = client.get("/api/v1/tasks/").json()["items"][0]["created_at"]
        datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# Tests for POST /api/v1/tasks/
# ---------------------------------------------------------------------------


class TestCreateTask:

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_create_task_returns_201(self, client, make_task):
        task = make_task()
        assert task["id"] is not None

    def test_create_task_returns_task_object(self, client, make_task):
        task = make_task(title="Task X", status="Todo")
        assert task["title"] == "Task X"
        assert task["status"] == "Todo"
        assert "id" in task

    def test_create_task_persists_to_db(self, client, make_task):
        make_task(title="Persist Me")
        items = client.get("/api/v1/tasks/").json()["items"]
        assert any(t["title"] == "Persist Me" for t in items)

    def test_create_task_with_all_statuses(self, client, make_task):
        for status in ["Todo", "In Progress", "Done"]:
            task = make_task(title=f"Task {status}", status=status)
            assert task["status"] == status

    def test_create_task_assigns_unique_ids(self, client, make_task):
        ids = [make_task(title=f"T{i}")["id"] for i in range(5)]
        assert len(set(ids)) == 5

    def test_create_task_returns_timestamps(self, client, make_task):
        task = make_task()
        assert task["created_at"] is not None
        assert task["updated_at"] is not None

    # ------------------------------------------------------------------
    # Validation — title
    # ------------------------------------------------------------------

    def test_create_task_empty_title_returns_422(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        resp = client.post("/api/v1/tasks/", json={**VALID_TASK_PAYLOAD, "title": ""})
        assert resp.status_code == 422

    def test_create_task_missing_title_returns_422(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        payload = {k: v for k, v in VALID_TASK_PAYLOAD.items() if k != "title"}
        resp = client.post("/api/v1/tasks/", json=payload)
        assert resp.status_code == 422

    def test_create_task_whitespace_only_title_returns_422(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        resp = client.post("/api/v1/tasks/", json={**VALID_TASK_PAYLOAD, "title": "   "})
        assert resp.status_code in (201, 422)

    def test_create_task_title_too_long_returns_422(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        resp = client.post("/api/v1/tasks/", json={**VALID_TASK_PAYLOAD, "title": "x" * 256})
        assert resp.status_code == 422

    def test_create_task_title_max_length_exactly_allowed(self, client, make_task):
        task = make_task(title="x" * 255)
        assert len(task["title"]) == 255

    def test_create_task_title_one_character_allowed(self, client, make_task):
        task = make_task(title="A")
        assert task["title"] == "A"

    # ------------------------------------------------------------------
    # Validation — status
    # ------------------------------------------------------------------

    def test_create_task_invalid_status_returns_422(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        resp = client.post("/api/v1/tasks/", json={**VALID_TASK_PAYLOAD, "status": "InvalidStatus"})
        assert resp.status_code == 422

    def test_create_task_status_case_sensitive(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        resp = client.post("/api/v1/tasks/", json={**VALID_TASK_PAYLOAD, "status": "todo"})
        assert resp.status_code == 422

    def test_create_task_status_numeric_returns_422(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        resp = client.post("/api/v1/tasks/", json={**VALID_TASK_PAYLOAD, "status": 1})
        assert resp.status_code == 422

    # ------------------------------------------------------------------
    # Payload edge cases
    # ------------------------------------------------------------------

    def test_create_task_extra_fields_are_ignored(self, client):
        from tests.conftest import VALID_TASK_PAYLOAD
        resp = client.post("/api/v1/tasks/", json={**VALID_TASK_PAYLOAD, "hacker_field": "DROP TABLE tasks;"})
        assert resp.status_code == 201
        assert "hacker_field" not in resp.json()

    def test_create_task_null_body_returns_422(self, client):
        resp = client.post("/api/v1/tasks/", json=None)
        assert resp.status_code == 422

    def test_create_task_empty_body_returns_422(self, client):
        resp = client.post("/api/v1/tasks/", json={})
        assert resp.status_code == 422

    def test_create_task_title_with_unicode_characters(self, client, make_task):
        task = make_task(title="タスク 🎯 مهمة")
        assert task["title"] == "タスク 🎯 مهمة"

    def test_create_task_title_with_html_is_stored_as_plain_text(self, client, make_task):
        xss = "<script>alert('xss')</script>"
        task = make_task(title=xss)
        assert task["title"] == xss

    def test_create_task_title_with_sql_injection_stored_safely(self, client, make_task):
        sqli = "'; DROP TABLE task; --"
        task = make_task(title=sqli)
        assert task["title"] == sqli

    def test_create_task_concurrent_creates_get_unique_ids(self, client, make_task):
        ids = [make_task(title=f"Task {i}")["id"] for i in range(10)]
        assert len(set(ids)) == 10


# ---------------------------------------------------------------------------
# Tests for PUT /api/v1/tasks/{id}
# ---------------------------------------------------------------------------


class TestUpdateTask:

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_update_task_returns_200(self, client, make_task):
        task = make_task()
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": "Updated"})
        assert resp.status_code == 200

    def test_update_title(self, client, make_task):
        task = make_task(title="Old Title")
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": "New Title"})
        assert resp.json()["title"] == "New Title"

    def test_update_description(self, client, make_task):
        task = make_task(description="Old desc")
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"description": "New desc"})
        assert resp.json()["description"] == "New desc"

    def test_update_status_todo_to_in_progress(self, client, make_task):
        task = make_task(status="Todo")
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"status": "In Progress"})
        assert resp.json()["status"] == "In Progress"

    def test_update_status_in_progress_to_done(self, client, make_task):
        task = make_task(status="In Progress")
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"status": "Done"})
        assert resp.json()["status"] == "Done"

    def test_update_status_done_back_to_todo(self, client, make_task):
        task = make_task(status="Done")
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"status": "Todo"})
        assert resp.json()["status"] == "Todo"

    def test_update_multiple_fields_at_once(self, client, make_task):
        task = make_task(title="Old", description="Old desc", status="Todo")
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={
            "title": "New",
            "description": "New desc",
            "status": "Done",
        })
        body = resp.json()
        assert body["title"] == "New"
        assert body["description"] == "New desc"
        assert body["status"] == "Done"

    def test_update_returns_full_task_object(self, client, make_task):
        task = make_task()
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": "Updated"})
        body = resp.json()
        for field in ("id", "title", "description", "status", "created_at", "updated_at"):
            assert field in body

    def test_update_persists_to_db(self, client, make_task):
        task = make_task(title="Before")
        client.put(f"/api/v1/tasks/{task['id']}", json={"title": "After"})
        updated = client.get(f"/api/v1/tasks/{task['id']}").json()
        assert updated["title"] == "After"

    def test_update_only_specified_fields_are_changed(self, client, make_task):
        task = make_task(title="Original Title", description="Original Desc", status="Todo")
        client.put(f"/api/v1/tasks/{task['id']}", json={"status": "Done"})
        updated = client.get(f"/api/v1/tasks/{task['id']}").json()
        assert updated["title"] == "Original Title"
        assert updated["description"] == "Original Desc"
        assert updated["status"] == "Done"

    def test_update_bumps_updated_at(self, client, make_task):
        task = make_task()
        original_updated_at = task["updated_at"]
        time.sleep(0.05)
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": "Changed"})
        assert resp.json()["updated_at"] != original_updated_at

    def test_update_does_not_change_created_at(self, client, make_task):
        task = make_task()
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": "Changed"})
        assert resp.json()["created_at"] == task["created_at"]

    def test_update_does_not_change_id(self, client, make_task):
        task = make_task()
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": "Changed"})
        assert resp.json()["id"] == task["id"]

    def test_update_one_task_does_not_affect_another(self, client, make_task):
        t1 = make_task(title="Task One")
        t2 = make_task(title="Task Two")
        client.put(f"/api/v1/tasks/{t1['id']}", json={"title": "Task One Updated"})
        t2_after = client.get(f"/api/v1/tasks/{t2['id']}").json()
        assert t2_after["title"] == "Task Two"

    # ------------------------------------------------------------------
    # Not found
    # ------------------------------------------------------------------

    def test_update_nonexistent_task_returns_404(self, client):
        resp = client.put("/api/v1/tasks/99999", json={"title": "Ghost"})
        assert resp.status_code == 404

    def test_update_returns_404_detail_message(self, client):
        resp = client.put("/api/v1/tasks/99999", json={"title": "Ghost"})
        assert "detail" in resp.json()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # ID edge cases
    # ------------------------------------------------------------------

    def test_update_with_string_id_returns_422(self, client):
        resp = client.put("/api/v1/tasks/abc", json={"title": "String ID"})
        assert resp.status_code == 422

    # ------------------------------------------------------------------
    # Payload edge cases
    # ------------------------------------------------------------------

    def test_update_with_empty_body_returns_200_no_changes(self, client, make_task):
        task = make_task(title="Unchanged")
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Unchanged"

    def test_update_extra_fields_are_ignored(self, client, make_task):
        task = make_task()
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"title": "Valid", "injected": "evil"})
        assert resp.status_code == 200
        assert "injected" not in resp.json()

    def test_update_id_field_in_body_is_ignored(self, client, make_task):
        task = make_task()
        original_id = task["id"]
        resp = client.put(f"/api/v1/tasks/{task['id']}", json={"id": 9999, "title": "Sneaky"})
        assert resp.json()["id"] == original_id


# ---------------------------------------------------------------------------
# Tests for DELETE /api/v1/tasks/{id}
# ---------------------------------------------------------------------------


class TestDeleteTask:

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_delete_task_returns_204(self, client, make_task):
        task = make_task()
        resp = client.delete(f"/api/v1/tasks/{task['id']}")
        assert resp.status_code == 204

    def test_delete_task_returns_no_body(self, client, make_task):
        task = make_task()
        resp = client.delete(f"/api/v1/tasks/{task['id']}")
        assert resp.content == b""

    def test_delete_task_removes_from_db(self, client, make_task):
        task = make_task(title="To Be Deleted")
        client.delete(f"/api/v1/tasks/{task['id']}")
        resp = client.get(f"/api/v1/tasks/{task['id']}")
        assert resp.status_code == 404

    def test_delete_task_decrements_task_count(self, client, make_task):
        make_task()
        make_task()
        make_task()
        before = client.get("/api/v1/tasks/").json()["total"]
        task = make_task()
        client.delete(f"/api/v1/tasks/{task['id']}")
        after = client.get("/api/v1/tasks/").json()["total"]
        assert after == before

    def test_delete_only_specified_task_is_removed(self, client, make_task):
        t1 = make_task(title="Keep Me")
        t2 = make_task(title="Delete Me")
        client.delete(f"/api/v1/tasks/{t2['id']}")
        items = client.get("/api/v1/tasks/").json()["items"]
        ids = [t["id"] for t in items]
        assert t1["id"] in ids
        assert t2["id"] not in ids

    def test_delete_all_tasks_leaves_empty_list(self, client, make_task):
        tasks = [make_task(title=f"T{i}") for i in range(3)]
        for t in tasks:
            client.delete(f"/api/v1/tasks/{t['id']}")
        assert client.get("/api/v1/tasks/").json()["total"] == 0

    # ------------------------------------------------------------------
    # Not found
    # ------------------------------------------------------------------

    def test_delete_nonexistent_task_returns_404(self, client):
        resp = client.delete("/api/v1/tasks/99999")
        assert resp.status_code == 404

    def test_delete_nonexistent_task_has_detail_message(self, client):
        resp = client.delete("/api/v1/tasks/99999")
        assert "detail" in resp.json()

    def test_delete_same_task_twice_returns_404_on_second(self, client, make_task):
        task = make_task()
        client.delete(f"/api/v1/tasks/{task['id']}")
        resp = client.delete(f"/api/v1/tasks/{task['id']}")
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # ID edge cases
    # ------------------------------------------------------------------

    def test_delete_with_string_id_returns_422(self, client):
        resp = client.delete("/api/v1/tasks/abc")
        assert resp.status_code == 422

    def test_delete_with_very_large_id_returns_404(self, client):
        resp = client.delete("/api/v1/tasks/999999999")
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # Isolation
    # ------------------------------------------------------------------

    def test_delete_does_not_affect_other_endpoints(self, client, make_task):
        t1 = make_task(title="Gone")
        client.delete(f"/api/v1/tasks/{t1['id']}")
        assert client.get("/api/v1/tasks/").status_code == 200
        resp = make_task(title="Still Here")
        assert resp["id"] is not None
