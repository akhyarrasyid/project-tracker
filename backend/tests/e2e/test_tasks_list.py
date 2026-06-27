"""E2E tests for GET /api/v1/tasks/ — list, pagination, filtering, search, sort."""
import pytest


class TestListTasksBasic:
    def test_returns_200(self, client):
        resp = client.get("/api/v1/tasks/")
        assert resp.status_code == 200

    def test_response_has_pagination_envelope(self, client):
        resp = client.get("/api/v1/tasks/")
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "size" in body
        assert "pages" in body

    def test_empty_db_returns_zero_total(self, client):
        resp = client.get("/api/v1/tasks/")
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_default_page_and_size(self, client):
        resp = client.get("/api/v1/tasks/")
        body = resp.json()
        assert body["page"] == 1
        assert body["size"] == 20

    def test_total_reflects_created_tasks(self, client, make_task):
        make_task(title="A")
        make_task(title="B")
        resp = client.get("/api/v1/tasks/")
        assert resp.json()["total"] == 2

    def test_task_response_has_all_26_fields(self, client, make_task):
        make_task()
        task = client.get("/api/v1/tasks/").json()["items"][0]
        required = [
            "id", "title", "description", "status", "priority",
            "department", "team", "assignee", "created_by",
            "created_at", "updated_at", "due_date", "completed_at",
            "story_points", "estimated_hours", "actual_hours",
            "progress_percentage", "attachments_count", "comments_count",
            "watchers_count", "sprint", "quarter", "risk_level",
            "customer_impact", "sla_hours", "dependencies", "tags",
        ]
        for field in required:
            assert field in task, f"Missing field: {field}"

    def test_default_sort_is_newest_first(self, client, make_task):
        t1 = make_task(title="First")
        t2 = make_task(title="Second")
        items = client.get("/api/v1/tasks/").json()["items"]
        ids = [t["id"] for t in items]
        assert ids.index(t2["id"]) < ids.index(t1["id"])


class TestListTasksPagination:
    def test_size_parameter(self, client, make_task):
        for i in range(10):
            make_task(title=f"Task {i}")
        resp = client.get("/api/v1/tasks/?size=3")
        assert len(resp.json()["items"]) == 3

    def test_page_two_returns_different_items(self, client, make_task):
        for i in range(10):
            make_task(title=f"Task {i}")
        p1 = set(t["id"] for t in client.get("/api/v1/tasks/?page=1&size=5").json()["items"])
        p2 = set(t["id"] for t in client.get("/api/v1/tasks/?page=2&size=5").json()["items"])
        assert not p1.intersection(p2)

    def test_pages_count_is_correct(self, client, make_task):
        for i in range(25):
            make_task(title=f"Task {i}")
        body = client.get("/api/v1/tasks/?size=10").json()
        assert body["total"] == 25
        assert body["pages"] == 3

    def test_size_max_100(self, client):
        resp = client.get("/api/v1/tasks/?size=101")
        assert resp.status_code == 422

    def test_page_zero_returns_422(self, client):
        resp = client.get("/api/v1/tasks/?page=0")
        assert resp.status_code == 422

    def test_beyond_last_page_returns_empty_items(self, client, make_task):
        make_task()
        body = client.get("/api/v1/tasks/?page=999").json()
        assert body["items"] == []
        assert body["total"] == 1


class TestListTasksFiltering:
    def test_filter_by_status(self, client, make_task):
        make_task(title="Todo", status="Todo")
        make_task(title="Done", status="Done")
        body = client.get("/api/v1/tasks/?status=Todo").json()
        assert body["total"] == 1
        assert body["items"][0]["status"] == "Todo"

    def test_filter_by_priority(self, client, make_task):
        make_task(priority="High")
        make_task(priority="Low")
        body = client.get("/api/v1/tasks/?priority=High").json()
        assert body["total"] == 1

    def test_filter_by_department(self, client, make_task):
        make_task(department="Engineering")
        make_task(department="Marketing")
        body = client.get("/api/v1/tasks/?department=Engineering").json()
        assert body["total"] == 1

    def test_filter_by_assignee(self, client, make_task):
        make_task(assignee="Alice Smith")
        make_task(assignee="Bob Jones")
        body = client.get("/api/v1/tasks/?assignee=Alice+Smith").json()
        assert body["total"] == 1

    def test_multiple_status_comma_separated(self, client, make_task):
        make_task(status="Todo")
        make_task(status="Done")
        make_task(status="Review")
        body = client.get("/api/v1/tasks/?status=Todo,Done").json()
        assert body["total"] == 2

    def test_no_match_filter_returns_empty(self, client, make_task):
        make_task(status="Todo")
        body = client.get("/api/v1/tasks/?status=Blocked").json()
        assert body["total"] == 0


class TestListTasksSearch:
    def test_search_by_title(self, client, make_task):
        make_task(title="Launch Campaign Alpha")
        make_task(title="Fix Login Bug")
        body = client.get("/api/v1/tasks/?search=campaign").json()
        assert body["total"] == 1

    def test_search_case_insensitive(self, client, make_task):
        make_task(title="LAUNCH CAMPAIGN")
        body = client.get("/api/v1/tasks/?search=launch").json()
        assert body["total"] == 1

    def test_search_by_description(self, client, make_task):
        make_task(title="Task A", description="unique_search_token_xyz")
        make_task(title="Task B", description="nothing here")
        body = client.get("/api/v1/tasks/?search=unique_search_token_xyz").json()
        assert body["total"] == 1

    def test_search_no_match(self, client, make_task):
        make_task(title="Something")
        body = client.get("/api/v1/tasks/?search=zzznomatch").json()
        assert body["total"] == 0


class TestListTasksSorting:
    def test_sort_by_id_asc(self, client, make_task):
        make_task(title="A")
        make_task(title="B")
        items = client.get("/api/v1/tasks/?sort_by=id&sort_order=asc").json()["items"]
        ids = [t["id"] for t in items]
        assert ids == sorted(ids)

    def test_sort_by_id_desc(self, client, make_task):
        make_task(title="A")
        make_task(title="B")
        items = client.get("/api/v1/tasks/?sort_by=id&sort_order=desc").json()["items"]
        ids = [t["id"] for t in items]
        assert ids == sorted(ids, reverse=True)

    def test_invalid_sort_order_returns_422(self, client):
        resp = client.get("/api/v1/tasks/?sort_order=sideways")
        assert resp.status_code == 422
