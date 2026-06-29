"""E2E coverage for project board loading and issue move semantics."""


class TestProjectBoard:
    def test_project_board_returns_column_counts_without_global_pagination(
        self, client, make_task
    ):
        todo_1 = make_task(title="Todo 1", status="Todo")
        todo_2 = make_task(title="Todo 2", status="Todo")
        review = make_task(title="Review 1", status="Review")

        response = client.get(
            f"/api/v1/projects/{client.seed['project_id']}/board?limit=1"
        )

        assert response.status_code == 200
        body = response.json()
        assert body["columns"]["Todo"]["total_count"] == 2
        assert len(body["columns"]["Todo"]["items"]) == 1
        assert body["columns"]["Review"]["total_count"] == 1
        assert body["columns"]["Review"]["items"][0]["id"] == review["id"]
        returned_ids = {item["id"] for item in body["columns"]["Todo"]["items"]}
        assert returned_ids <= {todo_1["id"], todo_2["id"]}

    def test_move_issue_reorders_within_target_column(self, client, make_task):
        todo_1 = make_task(title="Todo 1", status="Todo")
        todo_2 = make_task(title="Todo 2", status="Todo")
        moving = make_task(title="Moving", status="Review")

        response = client.patch(
            f"/api/v1/issues/{moving['id']}/move",
            json={
                "status": "Todo",
                "after_issue_id": todo_1["id"],
                "before_issue_id": todo_2["id"],
            },
        )

        assert response.status_code == 200, response.text
        moved = response.json()
        assert moved["status"] == "Todo"

        board = client.get(f"/api/v1/projects/{client.seed['project_id']}/board").json()
        todo_ids = [item["id"] for item in board["columns"]["Todo"]["items"]]
        assert todo_ids == [todo_1["id"], moving["id"], todo_2["id"]]
