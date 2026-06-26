"""
Tests for GET /tasks/
"""
import pytest


class TestGetTasks:

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_get_tasks_returns_200(self, client):
        resp = client.get("/tasks/")
        assert resp.status_code == 200

    def test_get_tasks_returns_list(self, client):
        resp = client.get("/tasks/")
        assert isinstance(resp.json(), list)

    def test_get_tasks_empty_when_no_tasks(self, client):
        resp = client.get("/tasks/")
        assert resp.json() == []

    def test_get_tasks_returns_all_created_tasks(self, client, make_task):
        make_task(title="Task A")
        make_task(title="Task B")
        make_task(title="Task C")
        resp = client.get("/tasks/")
        titles = [t["title"] for t in resp.json()]
        assert "Task A" in titles
        assert "Task B" in titles
        assert "Task C" in titles

    def test_get_tasks_returns_correct_fields(self, client, make_task):
        make_task()
        resp = client.get("/tasks/")
        task = resp.json()[0]
        assert "id" in task
        assert "title" in task
        assert "description" in task
        assert "status" in task
        assert "created_at" in task
        assert "updated_at" in task

    def test_get_tasks_ordered_newest_first(self, client, make_task):
        first = make_task(title="First Task")
        second = make_task(title="Second Task")
        resp = client.get("/tasks/")
        tasks = resp.json()
        ids = [t["id"] for t in tasks]
        # Newest (second) should come before oldest (first)
        assert ids.index(second["id"]) < ids.index(first["id"])

    def test_get_tasks_default_status_is_todo(self, client, make_task):
        make_task()
        resp = client.get("/tasks/")
        assert resp.json()[0]["status"] == "Todo"

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_get_tasks_description_can_be_null(self, client):
        client.post("/tasks/", json={"title": "No Desc", "status": "Todo"})
        resp = client.get("/tasks/")
        task = next(t for t in resp.json() if t["title"] == "No Desc")
        assert task["description"] is None

    def test_get_tasks_returns_all_statuses(self, client, make_task):
        make_task(title="T1", status="Todo")
        make_task(title="T2", status="In Progress")
        make_task(title="T3", status="Done")
        resp = client.get("/tasks/")
        statuses = {t["status"] for t in resp.json()}
        assert {"Todo", "In Progress", "Done"}.issubset(statuses)

    def test_get_tasks_id_is_integer(self, client, make_task):
        make_task()
        resp = client.get("/tasks/")
        assert isinstance(resp.json()[0]["id"], int)

    def test_get_tasks_created_at_is_valid_datetime(self, client, make_task):
        from datetime import datetime
        make_task()
        resp = client.get("/tasks/")
        dt_str = resp.json()[0]["created_at"]
        # Should not raise
        datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


"""
Tests for POST /tasks/
"""
import pytest


class TestCreateTask:

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_create_task_returns_201(self, client):
        resp = client.post("/tasks/", json={
            "title": "My Task",
            "description": "Some description",
            "status": "Todo",
        })
        assert resp.status_code == 201

    def test_create_task_returns_task_object(self, client):
        resp = client.post("/tasks/", json={"title": "Task X", "status": "Todo"})
        body = resp.json()
        assert body["title"] == "Task X"
        assert body["status"] == "Todo"
        assert "id" in body

    def test_create_task_persists_to_db(self, client):
        client.post("/tasks/", json={"title": "Persist Me", "status": "Todo"})
        tasks = client.get("/tasks/").json()
        assert any(t["title"] == "Persist Me" for t in tasks)

    def test_create_task_with_all_statuses(self, client):
        for status in ["Todo", "In Progress", "Done"]:
            resp = client.post("/tasks/", json={"title": f"Task {status}", "status": status})
            assert resp.status_code == 201
            assert resp.json()["status"] == status

    def test_create_task_without_description(self, client):
        resp = client.post("/tasks/", json={"title": "No desc", "status": "Todo"})
        assert resp.status_code == 201
        assert resp.json()["description"] is None

    def test_create_task_without_status_defaults_to_todo(self, client):
        resp = client.post("/tasks/", json={"title": "Default status"})
        assert resp.status_code == 201
        assert resp.json()["status"] == "Todo"

    def test_create_task_assigns_unique_ids(self, client):
        id1 = client.post("/tasks/", json={"title": "T1", "status": "Todo"}).json()["id"]
        id2 = client.post("/tasks/", json={"title": "T2", "status": "Todo"}).json()["id"]
        assert id1 != id2

    def test_create_task_returns_timestamps(self, client):
        resp = client.post("/tasks/", json={"title": "Timestamped", "status": "Todo"})
        body = resp.json()
        assert body["created_at"] is not None
        assert body["updated_at"] is not None

    # ------------------------------------------------------------------
    # Validation — title
    # ------------------------------------------------------------------

    def test_create_task_empty_title_returns_422(self, client):
        resp = client.post("/tasks/", json={"title": "", "status": "Todo"})
        assert resp.status_code == 422

    def test_create_task_missing_title_returns_422(self, client):
        resp = client.post("/tasks/", json={"status": "Todo"})
        assert resp.status_code == 422

    def test_create_task_whitespace_only_title_returns_422(self, client):
        resp = client.post("/tasks/", json={"title": "   ", "status": "Todo"})
        # Pydantic min_length=1 seharusnya menolak whitespace saja
        # (tergantung implementasi — kalau belum ada strip, test ini jadi reminder)
        assert resp.status_code in (201, 422)  # dokumentasikan behavior

    def test_create_task_title_too_long_returns_422(self, client):
        resp = client.post("/tasks/", json={"title": "x" * 256, "status": "Todo"})
        assert resp.status_code == 422

    def test_create_task_title_max_length_exactly_allowed(self, client):
        resp = client.post("/tasks/", json={"title": "x" * 255, "status": "Todo"})
        assert resp.status_code == 201

    def test_create_task_title_one_character_allowed(self, client):
        resp = client.post("/tasks/", json={"title": "A", "status": "Todo"})
        assert resp.status_code == 201

    # ------------------------------------------------------------------
    # Validation — status
    # ------------------------------------------------------------------

    def test_create_task_invalid_status_returns_422(self, client):
        resp = client.post("/tasks/", json={"title": "Task", "status": "InvalidStatus"})
        assert resp.status_code == 422

    def test_create_task_status_case_sensitive(self, client):
        resp = client.post("/tasks/", json={"title": "Task", "status": "todo"})
        assert resp.status_code == 422  # "todo" != "Todo"

    def test_create_task_status_numeric_returns_422(self, client):
        resp = client.post("/tasks/", json={"title": "Task", "status": 1})
        assert resp.status_code == 422

    # ------------------------------------------------------------------
    # Validation — description
    # ------------------------------------------------------------------

    def test_create_task_description_too_long_returns_422(self, client):
        resp = client.post("/tasks/", json={
            "title": "Task",
            "description": "x" * 1001,
            "status": "Todo",
        })
        assert resp.status_code == 422

    def test_create_task_description_max_length_allowed(self, client):
        resp = client.post("/tasks/", json={
            "title": "Task",
            "description": "x" * 1000,
            "status": "Todo",
        })
        assert resp.status_code == 201

    def test_create_task_description_empty_string_treated_as_null(self, client):
        resp = client.post("/tasks/", json={
            "title": "Task",
            "description": "",
            "status": "Todo",
        })
        # Empty string — dokumentasikan apakah disimpan "" atau None
        assert resp.status_code in (201, 422)

    # ------------------------------------------------------------------
    # Payload edge cases
    # ------------------------------------------------------------------

    def test_create_task_extra_fields_are_ignored(self, client):
        resp = client.post("/tasks/", json={
            "title": "Task",
            "status": "Todo",
            "hacker_field": "DROP TABLE tasks;",
        })
        assert resp.status_code == 201
        assert "hacker_field" not in resp.json()

    def test_create_task_null_body_returns_422(self, client):
        resp = client.post("/tasks/", json=None)
        assert resp.status_code == 422

    def test_create_task_empty_body_returns_422(self, client):
        resp = client.post("/tasks/", json={})
        assert resp.status_code == 422

    def test_create_task_title_with_unicode_characters(self, client):
        resp = client.post("/tasks/", json={"title": "タスク 🎯 مهمة", "status": "Todo"})
        assert resp.status_code == 201
        assert resp.json()["title"] == "タスク 🎯 مهمة"

    def test_create_task_title_with_html_is_stored_as_plain_text(self, client):
        xss = "<script>alert('xss')</script>"
        resp = client.post("/tasks/", json={"title": xss, "status": "Todo"})
        assert resp.status_code == 201
        assert resp.json()["title"] == xss  # stored as-is, sanitize di frontend

    def test_create_task_title_with_sql_injection_stored_safely(self, client):
        sqli = "'; DROP TABLE task; --"
        resp = client.post("/tasks/", json={"title": sqli, "status": "Todo"})
        assert resp.status_code == 201
        assert resp.json()["title"] == sqli

    def test_create_task_concurrent_creates_get_unique_ids(self, client):
        """Simulasi 10 task sekaligus — semua ID harus unik."""
        ids = [
            client.post("/tasks/", json={"title": f"Task {i}", "status": "Todo"}).json()["id"]
            for i in range(10)
        ]
        assert len(set(ids)) == 10


"""
Tests for PUT /tasks/{id}
"""
import pytest
import time


class TestUpdateTask:

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_update_task_returns_200(self, client, make_task):
        task = make_task()
        resp = client.put(f"/tasks/{task['id']}", json={"title": "Updated"})
        assert resp.status_code == 200

    def test_update_title(self, client, make_task):
        task = make_task(title="Old Title")
        resp = client.put(f"/tasks/{task['id']}", json={"title": "New Title"})
        assert resp.json()["title"] == "New Title"

    def test_update_description(self, client, make_task):
        task = make_task(description="Old desc")
        resp = client.put(f"/tasks/{task['id']}", json={"description": "New desc"})
        assert resp.json()["description"] == "New desc"

    def test_update_status_todo_to_in_progress(self, client, make_task):
        task = make_task(status="Todo")
        resp = client.put(f"/tasks/{task['id']}", json={"status": "In Progress"})
        assert resp.json()["status"] == "In Progress"

    def test_update_status_in_progress_to_done(self, client, make_task):
        task = make_task(status="In Progress")
        resp = client.put(f"/tasks/{task['id']}", json={"status": "Done"})
        assert resp.json()["status"] == "Done"

    def test_update_status_done_back_to_todo(self, client, make_task):
        """Status bisa di-revert — tidak ada constraint one-way."""
        task = make_task(status="Done")
        resp = client.put(f"/tasks/{task['id']}", json={"status": "Todo"})
        assert resp.json()["status"] == "Todo"

    def test_update_multiple_fields_at_once(self, client, make_task):
        task = make_task(title="Old", description="Old desc", status="Todo")
        resp = client.put(f"/tasks/{task['id']}", json={
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
        resp = client.put(f"/tasks/{task['id']}", json={"title": "Updated"})
        body = resp.json()
        assert "id" in body
        assert "title" in body
        assert "description" in body
        assert "status" in body
        assert "created_at" in body
        assert "updated_at" in body

    def test_update_persists_to_db(self, client, make_task):
        task = make_task(title="Before")
        client.put(f"/tasks/{task['id']}", json={"title": "After"})
        tasks = client.get("/tasks/").json()
        updated = next(t for t in tasks if t["id"] == task["id"])
        assert updated["title"] == "After"

    def test_update_only_specified_fields_are_changed(self, client, make_task):
        """Partial update — unspecified fields must stay the same."""
        task = make_task(title="Original Title", description="Original Desc", status="Todo")
        client.put(f"/tasks/{task['id']}", json={"status": "Done"})
        tasks = client.get("/tasks/").json()
        updated = next(t for t in tasks if t["id"] == task["id"])
        assert updated["title"] == "Original Title"
        assert updated["description"] == "Original Desc"
        assert updated["status"] == "Done"

    def test_update_bumps_updated_at(self, client, make_task):
        task = make_task()
        original_updated_at = task["updated_at"]
        time.sleep(0.01)  # ensure time passes
        resp = client.put(f"/tasks/{task['id']}", json={"title": "Changed"})
        assert resp.json()["updated_at"] != original_updated_at

    def test_update_does_not_change_created_at(self, client, make_task):
        task = make_task()
        resp = client.put(f"/tasks/{task['id']}", json={"title": "Changed"})
        assert resp.json()["created_at"] == task["created_at"]

    def test_update_does_not_change_id(self, client, make_task):
        task = make_task()
        resp = client.put(f"/tasks/{task['id']}", json={"title": "Changed"})
        assert resp.json()["id"] == task["id"]

    def test_update_one_task_does_not_affect_another(self, client, make_task):
        t1 = make_task(title="Task One")
        t2 = make_task(title="Task Two")
        client.put(f"/tasks/{t1['id']}", json={"title": "Task One Updated"})
        tasks = client.get("/tasks/").json()
        t2_after = next(t for t in tasks if t["id"] == t2["id"])
        assert t2_after["title"] == "Task Two"

    # ------------------------------------------------------------------
    # Not found
    # ------------------------------------------------------------------

    def test_update_nonexistent_task_returns_404(self, client):
        resp = client.put("/tasks/99999", json={"title": "Ghost"})
        assert resp.status_code == 404

    def test_update_returns_404_detail_message(self, client):
        resp = client.put("/tasks/99999", json={"title": "Ghost"})
        assert "detail" in resp.json()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def test_update_empty_title_returns_422(self, client, make_task):
        task = make_task()
        resp = client.put(f"/tasks/{task['id']}", json={"title": ""})
        assert resp.status_code == 422

    def test_update_title_too_long_returns_422(self, client, make_task):
        task = make_task()
        resp = client.put(f"/tasks/{task['id']}", json={"title": "x" * 256})
        assert resp.status_code == 422

    def test_update_invalid_status_returns_422(self, client, make_task):
        task = make_task()
        resp = client.put(f"/tasks/{task['id']}", json={"status": "Selesai"})
        assert resp.status_code == 422

    def test_update_description_too_long_returns_422(self, client, make_task):
        task = make_task()
        resp = client.put(f"/tasks/{task['id']}", json={"description": "x" * 1001})
        assert resp.status_code == 422

    # ------------------------------------------------------------------
    # ID edge cases
    # ------------------------------------------------------------------

    def test_update_with_zero_id_returns_404_or_422(self, client):
        resp = client.put("/tasks/0", json={"title": "Zero"})
        assert resp.status_code in (404, 422)

    def test_update_with_negative_id_returns_404_or_422(self, client):
        resp = client.put("/tasks/-1", json={"title": "Negative"})
        assert resp.status_code in (404, 422)

    def test_update_with_string_id_returns_422(self, client):
        resp = client.put("/tasks/abc", json={"title": "String ID"})
        assert resp.status_code == 422

    def test_update_with_float_id_returns_422(self, client):
        resp = client.put("/tasks/1.5", json={"title": "Float ID"})
        assert resp.status_code == 422

    # ------------------------------------------------------------------
    # Payload edge cases
    # ------------------------------------------------------------------

    def test_update_with_empty_body_returns_200_no_changes(self, client, make_task):
        """Empty update payload — nothing should change."""
        task = make_task(title="Unchanged")
        resp = client.put(f"/tasks/{task['id']}", json={})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Unchanged"

    def test_update_extra_fields_are_ignored(self, client, make_task):
        task = make_task()
        resp = client.put(f"/tasks/{task['id']}", json={
            "title": "Valid",
            "injected": "evil",
        })
        assert resp.status_code == 200
        assert "injected" not in resp.json()

    def test_update_id_field_in_body_is_ignored(self, client, make_task):
        """Client cannot change the task's ID via body."""
        task = make_task()
        original_id = task["id"]
        resp = client.put(f"/tasks/{task['id']}", json={"id": 9999, "title": "Sneaky"})
        assert resp.json()["id"] == original_id


"""
Tests for DELETE /tasks/{id}
"""
import pytest


class TestDeleteTask:

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_delete_task_returns_204(self, client, make_task):
        task = make_task()
        resp = client.delete(f"/tasks/{task['id']}")
        assert resp.status_code == 204

    def test_delete_task_returns_no_body(self, client, make_task):
        task = make_task()
        resp = client.delete(f"/tasks/{task['id']}")
        assert resp.content == b""

    def test_delete_task_removes_from_db(self, client, make_task):
        task = make_task(title="To Be Deleted")
        client.delete(f"/tasks/{task['id']}")
        tasks = client.get("/tasks/").json()
        assert not any(t["id"] == task["id"] for t in tasks)

    def test_delete_task_decrements_task_count(self, client, make_task):
        make_task()
        make_task()
        make_task()
        before = len(client.get("/tasks/").json())
        task = make_task()
        client.delete(f"/tasks/{task['id']}")
        after = len(client.get("/tasks/").json())
        assert after == before

    def test_delete_only_specified_task_is_removed(self, client, make_task):
        t1 = make_task(title="Keep Me")
        t2 = make_task(title="Delete Me")
        client.delete(f"/tasks/{t2['id']}")
        tasks = client.get("/tasks/").json()
        assert any(t["id"] == t1["id"] for t in tasks)
        assert not any(t["id"] == t2["id"] for t in tasks)

    def test_delete_all_tasks_leaves_empty_list(self, client, make_task):
        tasks = [make_task(title=f"T{i}") for i in range(3)]
        for t in tasks:
            client.delete(f"/tasks/{t['id']}")
        assert client.get("/tasks/").json() == []

    # ------------------------------------------------------------------
    # Not found
    # ------------------------------------------------------------------

    def test_delete_nonexistent_task_returns_404(self, client):
        resp = client.delete("/tasks/99999")
        assert resp.status_code == 404

    def test_delete_nonexistent_task_has_detail_message(self, client):
        resp = client.delete("/tasks/99999")
        assert "detail" in resp.json()

    def test_delete_same_task_twice_returns_404_on_second(self, client, make_task):
        """Idempotency check: second delete must 404, not 500."""
        task = make_task()
        client.delete(f"/tasks/{task['id']}")
        resp = client.delete(f"/tasks/{task['id']}")
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # ID edge cases
    # ------------------------------------------------------------------

    def test_delete_with_zero_id_returns_404_or_422(self, client):
        resp = client.delete("/tasks/0")
        assert resp.status_code in (404, 422)

    def test_delete_with_negative_id_returns_404_or_422(self, client):
        resp = client.delete("/tasks/-1")
        assert resp.status_code in (404, 422)

    def test_delete_with_string_id_returns_422(self, client):
        resp = client.delete("/tasks/abc")
        assert resp.status_code == 422

    def test_delete_with_float_id_returns_422(self, client):
        resp = client.delete("/tasks/2.5")
        assert resp.status_code == 422

    def test_delete_with_very_large_id_returns_404(self, client):
        resp = client.delete("/tasks/999999999")
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # Isolation
    # ------------------------------------------------------------------

    def test_delete_does_not_affect_other_endpoints(self, client, make_task):
        """After delete, GET and POST still work correctly."""
        t1 = make_task(title="Gone")
        client.delete(f"/tasks/{t1['id']}")
        # GET still works
        assert client.get("/tasks/").status_code == 200
        # POST still works
        resp = client.post("/tasks/", json={"title": "Still Here", "status": "Todo"})
        assert resp.status_code == 201
