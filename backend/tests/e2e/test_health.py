"""E2E tests for GET /api/v1/tasks/{id}, /health, /readiness."""
import pytest


class TestGetTaskById:

    def test_get_by_id_returns_200(self, client, make_task):
        task = make_task()
        resp = client.get(f"/api/v1/tasks/{task['id']}")
        assert resp.status_code == 200

    def test_get_by_id_returns_correct_task(self, client, make_task):
        task = make_task(title="Specific Task")
        resp = client.get(f"/api/v1/tasks/{task['id']}")
        assert resp.json()["title"] == "Specific Task"

    def test_get_by_id_has_all_26_fields(self, client, make_task):
        task = make_task()
        resp = client.get(f"/api/v1/tasks/{task['id']}")
        body = resp.json()
        for field in [
            "id", "title", "description", "status", "priority",
            "department", "team", "assignee", "created_by",
            "created_at", "updated_at", "due_date", "completed_at",
            "story_points", "estimated_hours", "actual_hours",
            "progress_percentage", "attachments_count", "comments_count",
            "watchers_count", "sprint", "quarter", "risk_level",
            "customer_impact", "sla_hours", "dependencies", "tags",
        ]:
            assert field in body, f"Missing field: {field}"

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get("/api/v1/tasks/99999")
        assert resp.status_code == 404

    def test_get_nonexistent_has_detail_and_error_type(self, client):
        resp = client.get("/api/v1/tasks/99999")
        body = resp.json()
        assert "detail" in body
        assert body.get("error_type") == "not_found"

    def test_get_string_id_returns_422(self, client):
        resp = client.get("/api/v1/tasks/abc")
        assert resp.status_code == 422


class TestHealthEndpoints:

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_body_has_status_healthy(self, client):
        resp = client.get("/health")
        assert resp.json()["status"] == "healthy"

    def test_health_body_has_version(self, client):
        resp = client.get("/health")
        assert "version" in resp.json()

    def test_readiness_returns_200(self, client):
        resp = client.get("/readiness")
        assert resp.status_code == 200

    def test_readiness_body_has_status_ready(self, client):
        resp = client.get("/readiness")
        assert resp.json()["status"] == "ready"
