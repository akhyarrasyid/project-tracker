"""E2E tests for canonical /api/v1/issues compatibility routes."""


class TestIssuesAlias:
    def test_list_issues_matches_tasks_shape(self, client, make_task):
        make_task(title="Issue list")
        body = client.get("/api/v1/issues/").json()
        assert body["total"] == 1
        assert body["items"][0]["key"] == "PRJ-1"

    def test_get_issue_by_key(self, client, make_task):
        issue = make_task(title="Lookup issue")
        resp = client.get(f"/api/v1/issues/{issue['key']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == issue["id"]

    def test_update_issue_by_key(self, client, make_task):
        issue = make_task(title="Before update")
        resp = client.put(
            f"/api/v1/issues/{issue['key']}",
            json={"title": "After update", "is_blocked": True},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "After update"
        assert resp.json()["is_blocked"] is True

    def test_delete_issue_by_key(self, client, make_task):
        issue = make_task(title="Delete me")
        resp = client.delete(f"/api/v1/issues/{issue['key']}")
        assert resp.status_code == 204
        list_body = client.get("/api/v1/issues/").json()
        assert list_body["total"] == 0
