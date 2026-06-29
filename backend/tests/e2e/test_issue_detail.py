import datetime

from app.core.security import get_current_user
from app.db.models.activity_log import ActivityLog
from app.db.models.project_member import ProjectMember
from app.db.models.task import Task
from app.db.models.user import User
from app.main import app
from tests.conftest import seed_test_hierarchy


def _make_project_member(db_session, seed, username: str, project_role: str) -> User:
    user = User(
        email=f"{username}@tracker.com",
        username=username,
        full_name=username.replace("_", " ").title(),
        hashed_password="hashed",
        role="worker",
        team_id=seed["team_id"],
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        ProjectMember(
            project_id=seed["project_id"],
            user_id=user.id,
            project_role=project_role,
        )
    )
    db_session.commit()
    return user


class TestIssueDetailApi:
    def test_patch_issue_with_expected_version_increments_version(self, client, make_task):
        issue = make_task(title="Concurrent issue")

        response = client.patch(
            f"/api/v1/issues/{issue['id']}",
            json={"priority": "High", "expected_version": issue["version"]},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["priority"] == "High"
        assert body["version"] == issue["version"] + 1

    def test_patch_issue_stale_version_returns_409_with_latest_issue(self, client, make_task):
        issue = make_task(title="Stale issue")
        first = client.patch(
            f"/api/v1/issues/{issue['id']}",
            json={"title": "Fresh title", "expected_version": issue["version"]},
        )
        assert first.status_code == 200

        stale = client.patch(
            f"/api/v1/issues/{issue['id']}",
            json={"priority": "Critical", "expected_version": issue["version"]},
        )

        assert stale.status_code == 409
        detail = stale.json()["detail"]
        assert detail["message"] == "Issue version is stale"
        assert detail["latest_issue"]["title"] == "Fresh title"
        assert detail["latest_issue"]["version"] == issue["version"] + 1

    def test_patch_issue_rejects_parent_from_other_project(self, client, make_task):
        issue = make_task(title="Child")
        other_parent = make_task(title="Other parent", department="Legal")

        response = client.patch(
            f"/api/v1/issues/{issue['id']}",
            json={"parent_id": other_parent["id"], "expected_version": issue["version"]},
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "Parent issue must belong to the same project"

    def test_patch_issue_rejects_self_parent(self, client, make_task):
        issue = make_task(title="Self parent")

        response = client.patch(
            f"/api/v1/issues/{issue['id']}",
            json={"parent_id": issue["id"], "expected_version": issue["version"]},
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "Issue cannot be its own parent"

    def test_patch_issue_rejects_simple_circular_parent_chain(self, client, make_task):
        parent = make_task(title="Parent")
        child = client.patch(
            f"/api/v1/issues/{make_task(title='Child')['id']}",
            json={"parent_id": parent["id"], "expected_version": 1},
        ).json()

        response = client.patch(
            f"/api/v1/issues/{parent['id']}",
            json={"parent_id": child["id"], "expected_version": parent["version"]},
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "Circular issue hierarchy is not allowed"

    def test_no_op_patch_does_not_create_activity(self, client, db_session, make_task):
        issue = make_task(title="Stable title")
        before_count = (
            db_session.query(ActivityLog).filter(ActivityLog.task_id == issue["id"]).count()
        )

        response = client.patch(
            f"/api/v1/issues/{issue['id']}",
            json={"title": "Stable title", "expected_version": issue["version"]},
        )

        assert response.status_code == 200
        refreshed = client.get(f"/api/v1/issues/{issue['id']}").json()
        after_count = (
            db_session.query(ActivityLog).filter(ActivityLog.task_id == issue["id"]).count()
        )
        assert refreshed["version"] == issue["version"]
        assert after_count == before_count

    def test_list_comments_allows_viewer_but_create_rejects_viewer(self, client, db_session, make_task):
        seed = seed_test_hierarchy(db_session)
        viewer = _make_project_member(db_session, seed, "viewer_user", "VIEWER")
        issue = make_task(title="Commentable")

        def override_get_current_user():
            return viewer

        app.dependency_overrides[get_current_user] = override_get_current_user
        try:
            list_response = client.get(f"/api/v1/issues/{issue['id']}/comments")
            create_response = client.post(
                f"/api/v1/issues/{issue['id']}/comments",
                json={"content": "Viewer should fail"},
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert list_response.status_code == 200
        assert list_response.json() == []
        assert create_response.status_code == 403

    def test_create_comment_rejects_empty_content(self, client, make_task):
        issue = make_task(title="Empty comment")

        response = client.post(
            f"/api/v1/issues/{issue['id']}/comments",
            json={"content": "   "},
        )

        assert response.status_code == 422

    def test_create_comment_returns_author_summary_and_updates_activity(self, client, make_task):
        issue = make_task(title="Discuss me")

        comment_response = client.post(
            f"/api/v1/issues/{issue['id']}/comments",
            json={"content": "Please verify callback retries."},
        )

        assert comment_response.status_code == 201, comment_response.text
        comment = comment_response.json()
        assert comment["author"]["username"] == "admin"
        assert comment["content"] == "Please verify callback retries."

        issue_response = client.get(f"/api/v1/issues/{issue['id']}")
        activities_response = client.get(f"/api/v1/issues/{issue['id']}/activities")
        assert issue_response.json()["comments_count"] == 1
        assert any(
            item["action"] == "Comment Created" for item in activities_response.json()
        )

    def test_patch_issue_records_activity_for_due_date_and_parent(self, client, make_task):
        parent = make_task(title="Parent")
        issue = make_task(title="Child issue")

        response = client.patch(
            f"/api/v1/issues/{issue['id']}",
            json={
                "due_date": "2026-07-05",
                "parent_id": parent["id"],
                "expected_version": issue["version"],
            },
        )

        assert response.status_code == 200
        activities = client.get(f"/api/v1/issues/{issue['id']}/activities").json()
        fields = {item["field"] for item in activities}
        assert "due_date" in fields
        assert "parent_id" in fields

    def test_move_issue_with_stale_version_returns_409(self, client, make_task):
        todo = make_task(title="Todo target", status="Todo")
        moving = make_task(title="Moving", status="Review")
        moved = client.patch(
            f"/api/v1/issues/{moving['id']}/move",
            json={"status": "Todo", "after_issue_id": todo["id"], "expected_version": moving["version"]},
        )
        assert moved.status_code == 200

        stale = client.patch(
            f"/api/v1/issues/{moving['id']}/move",
            json={"status": "Review", "expected_version": moving["version"]},
        )
        assert stale.status_code == 409
        assert stale.json()["detail"]["latest_issue"]["version"] == moving["version"] + 1

    def test_delete_issue_by_id_enforces_member_restriction(self, client, db_session):
        seed = seed_test_hierarchy(db_session)
        member = seed["worker"]
        issue = Task(
            title="Admin owned",
            description="No delete",
            project_id=seed["project_id"],
            created_by_id=seed["admin"].id,
            due_date=datetime.date(2026, 7, 1),
            story_points=3,
            estimated_hours=8,
            actual_hours=0,
            progress_percentage=0,
            quarter="Q3",
            risk_level="Low",
            customer_impact="None",
            sla_hours=48,
            dependencies=[],
            tags=[],
            number=1,
            rank=1024,
        )
        db_session.add(issue)
        db_session.commit()

        def override_get_current_user():
            return member

        app.dependency_overrides[get_current_user] = override_get_current_user
        try:
            response = client.delete(f"/api/v1/issues/{issue.id}")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 403

    def test_compatibility_route_update_issue_by_key_still_works(self, client, make_task):
        issue = make_task(title="Compat issue")

        response = client.put(
            f"/api/v1/issues/{issue['key']}",
            json={"title": "Compat updated"},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Compat updated"
