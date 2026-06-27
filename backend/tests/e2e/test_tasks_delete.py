"""E2E tests for DELETE /api/v1/tasks/{id}."""
import pytest


class TestDeleteTask:

    def test_delete_returns_204(self, client, make_task):
        task = make_task()
        resp = client.delete(f"/api/v1/tasks/{task['id']}")
        assert resp.status_code == 204

    def test_delete_returns_no_body(self, client, make_task):
        task = make_task()
        resp = client.delete(f"/api/v1/tasks/{task['id']}")
        assert resp.content == b""

    def test_delete_removes_from_db(self, client, make_task):
        task = make_task(title="To Be Deleted")
        client.delete(f"/api/v1/tasks/{task['id']}")
        resp = client.get(f"/api/v1/tasks/{task['id']}")
        assert resp.status_code == 404

    def test_delete_decrements_total(self, client, make_task):
        make_task()
        make_task()
        make_task()
        before = client.get("/api/v1/tasks/").json()["total"]
        task = make_task()
        client.delete(f"/api/v1/tasks/{task['id']}")
        after = client.get("/api/v1/tasks/").json()["total"]
        assert after == before

    def test_delete_only_removes_target(self, client, make_task):
        t1 = make_task(title="Keep Me")
        t2 = make_task(title="Delete Me")
        client.delete(f"/api/v1/tasks/{t2['id']}")
        items = client.get("/api/v1/tasks/").json()["items"]
        ids = [t["id"] for t in items]
        assert t1["id"] in ids
        assert t2["id"] not in ids

    def test_delete_all_leaves_empty(self, client, make_task):
        tasks = [make_task(title=f"T{i}") for i in range(3)]
        for t in tasks:
            client.delete(f"/api/v1/tasks/{t['id']}")
        assert client.get("/api/v1/tasks/").json()["total"] == 0

    # ── Not found ─────────────────────────────────────────────────────────────

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/v1/tasks/99999")
        assert resp.status_code == 404

    def test_delete_same_task_twice_returns_404_on_second(self, client, make_task):
        task = make_task()
        client.delete(f"/api/v1/tasks/{task['id']}")
        resp = client.delete(f"/api/v1/tasks/{task['id']}")
        assert resp.status_code == 404

    # ── ID edge cases ─────────────────────────────────────────────────────────

    def test_delete_string_id_returns_422(self, client):
        resp = client.delete("/api/v1/tasks/abc")
        assert resp.status_code == 422

    def test_delete_large_nonexistent_id_returns_404(self, client):
        resp = client.delete("/api/v1/tasks/999999999")
        assert resp.status_code == 404

    # ── Isolation ─────────────────────────────────────────────────────────────

    def test_delete_does_not_break_other_endpoints(self, client, make_task):
        t1 = make_task(title="Gone")
        client.delete(f"/api/v1/tasks/{t1['id']}")
        assert client.get("/api/v1/tasks/").status_code == 200
        t2 = make_task(title="Still here")
        assert t2["id"] is not None
