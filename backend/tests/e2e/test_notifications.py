import pytest

from app.core.security import get_current_user
from app.db.models.notification import Notification
from app.db.models.project_member import ProjectMember
from app.db.models.task import Task
from app.db.models.user import User
from app.db.models.watcher import Watcher
from app.main import app
from app.services.notification_service import NotificationService
from tests.conftest import seed_test_hierarchy


def _make_project_user(
    db_session,
    *,
    seed,
    username: str,
    project_role: str | None,
    full_name: str | None = None,
) -> User:
    user = User(
        email=f"{username}@tracker.com",
        username=username,
        full_name=full_name or username.replace("_", " ").title(),
        hashed_password="hashed",
        role="worker",
        team_id=seed["team_id"],
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    if project_role is not None:
        db_session.add(
            ProjectMember(
                project_id=seed["project_id"],
                user_id=user.id,
                project_role=project_role,
            )
        )
    db_session.commit()
    return user


@pytest.fixture
def as_user():
    def _as_user(user: User):
        def override_get_current_user():
            return user

        app.dependency_overrides[get_current_user] = override_get_current_user

    yield _as_user
    app.dependency_overrides.pop(get_current_user, None)


class TestNotificationsApi:
    def test_list_notifications_only_returns_owned_items_and_unread_count(
        self, client, db_session, make_task, as_user
    ):
        seed = seed_test_hierarchy(db_session)
        worker = seed["worker"]
        viewer = _make_project_user(
            db_session, seed=seed, username="viewer_user", project_role="VIEWER"
        )
        issue = make_task(title="Inbox target", assignee="worker")
        task = db_session.query(Task).filter(Task.id == issue["id"]).one()

        NotificationService.notify_issue_assigned(
            db_session, issue=task, actor_id=seed["admin"].id, assignee_id=worker.id
        )
        NotificationService.notify_issue_assigned(
            db_session, issue=task, actor_id=seed["admin"].id, assignee_id=viewer.id
        )
        db_session.commit()

        as_user(worker)
        response = client.get("/api/v1/notifications")
        unread_response = client.get("/api/v1/notifications/unread-count")

        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["type"] == "issue_assigned"
        assert body["items"][0]["issue"]["key"] == issue["key"]
        assert body["items"][0]["route_target"] == f"/issues/{issue['key']}"
        assert unread_response.json()["unread_count"] == 1

    def test_notification_cursor_pagination_is_stable(self, client, db_session, make_task, as_user):
        seed = seed_test_hierarchy(db_session)
        worker = seed["worker"]
        issue = make_task(title="Cursor issue")
        task = db_session.query(Task).filter(Task.id == issue["id"]).one()

        for index in range(3):
            task.version += 1
            NotificationService.notify_issue_assigned(
                db_session,
                issue=task,
                actor_id=seed["admin"].id,
                assignee_id=worker.id,
            )
        db_session.commit()

        as_user(worker)
        first = client.get("/api/v1/notifications?limit=2")
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert len(first_body["items"]) == 2
        assert first_body["next_cursor"] is not None

        second = client.get(f"/api/v1/notifications?limit=2&cursor={first_body['next_cursor']}")
        assert second.status_code == 200, second.text
        second_body = second.json()
        assert len(second_body["items"]) == 1
        first_ids = {item["id"] for item in first_body["items"]}
        second_ids = {item["id"] for item in second_body["items"]}
        assert first_ids.isdisjoint(second_ids)

    def test_mark_read_unread_and_mark_all_read_are_idempotent(
        self, client, db_session, make_task, as_user
    ):
        seed = seed_test_hierarchy(db_session)
        worker = seed["worker"]
        issue = make_task(title="Read state issue")
        task = db_session.query(Task).filter(Task.id == issue["id"]).one()

        task.version = 1
        NotificationService.notify_issue_assigned(
            db_session, issue=task, actor_id=seed["admin"].id, assignee_id=worker.id
        )
        task.version = 2
        NotificationService.notify_issue_assigned(
            db_session,
            issue=task,
            actor_id=seed["admin"].id,
            assignee_id=worker.id,
        )
        db_session.commit()
        notifications = (
            db_session.query(Notification)
            .filter(Notification.recipient_id == worker.id)
            .order_by(Notification.id.asc())
            .all()
        )

        as_user(worker)
        read_response = client.patch(f"/api/v1/notifications/{notifications[0].id}/read")
        assert read_response.status_code == 200
        assert read_response.json()["notification"]["is_read"] is True

        repeat_read = client.patch(f"/api/v1/notifications/{notifications[0].id}/read")
        assert repeat_read.status_code == 200
        assert repeat_read.json()["notification"]["is_read"] is True

        unread_response = client.patch(
            f"/api/v1/notifications/{notifications[0].id}/unread"
        )
        assert unread_response.status_code == 200
        assert unread_response.json()["notification"]["is_read"] is False

        mark_all = client.post("/api/v1/notifications/mark-all-read")
        assert mark_all.status_code == 200
        assert mark_all.json()["updated_count"] == 2

        again = client.post("/api/v1/notifications/mark-all-read")
        assert again.status_code == 200
        assert again.json()["updated_count"] == 0

    def test_notification_routes_reject_access_to_other_users_notifications(
        self, client, db_session, make_task, as_user
    ):
        seed = seed_test_hierarchy(db_session)
        worker = seed["worker"]
        viewer = _make_project_user(
            db_session, seed=seed, username="viewer_only", project_role="VIEWER"
        )
        issue = make_task(title="Private inbox issue", assignee="worker")
        task = db_session.query(Task).filter(Task.id == issue["id"]).one()

        NotificationService.notify_issue_assigned(
            db_session, issue=task, actor_id=seed["admin"].id, assignee_id=worker.id
        )
        db_session.commit()
        notification = (
            db_session.query(Notification)
            .filter(Notification.recipient_id == worker.id)
            .one()
        )

        as_user(viewer)
        response = client.patch(f"/api/v1/notifications/{notification.id}/read")

        assert response.status_code == 404


class TestWatchersApi:
    def test_watch_unwatch_is_idempotent_and_viewer_can_watch_self(
        self, client, db_session, make_task, as_user
    ):
        seed = seed_test_hierarchy(db_session)
        viewer = _make_project_user(
            db_session, seed=seed, username="viewer_watch", project_role="VIEWER"
        )
        issue = make_task(title="Viewer watch issue")

        as_user(viewer)
        first_watch = client.post(f"/api/v1/issues/{issue['id']}/watchers/me")
        second_watch = client.post(f"/api/v1/issues/{issue['id']}/watchers/me")
        first_unwatch = client.delete(f"/api/v1/issues/{issue['id']}/watchers/me")
        second_unwatch = client.delete(f"/api/v1/issues/{issue['id']}/watchers/me")

        assert first_watch.status_code == 200
        assert first_watch.json()["is_watching"] is True
        assert second_watch.status_code == 200
        assert second_watch.json()["count"] == first_watch.json()["count"]
        assert first_unwatch.status_code == 200
        assert first_unwatch.json()["is_watching"] is False
        assert second_unwatch.status_code == 200
        assert second_unwatch.json()["count"] == first_unwatch.json()["count"]

        watcher_rows = (
            db_session.query(Watcher)
            .filter(Watcher.task_id == issue["id"], Watcher.user_id == viewer.id)
            .all()
        )
        assert len(watcher_rows) == 1
        assert watcher_rows[0].is_watching is False

    def test_only_owner_can_manage_other_watchers(self, client, db_session, make_task, as_user):
        seed = seed_test_hierarchy(db_session)
        member = seed["worker"]
        target = _make_project_user(
            db_session, seed=seed, username="observer_user", project_role="VIEWER"
        )
        issue = make_task(title="Managed watch issue")

        as_user(member)
        forbidden = client.post(f"/api/v1/issues/{issue['id']}/watchers/{target.id}")
        assert forbidden.status_code == 403

        as_user(seed["admin"])
        allowed = client.post(f"/api/v1/issues/{issue['id']}/watchers/{target.id}")
        assert allowed.status_code == 200
        assert any(item["id"] == target.id for item in allowed.json()["watchers"])

    def test_auto_watch_creator_assignee_commenter_and_mentions_generate_notifications(
        self, client, db_session, make_task, as_user
    ):
        seed = seed_test_hierarchy(db_session)
        worker = seed["worker"]
        viewer = _make_project_user(
            db_session,
            seed=seed,
            username="viewer_ping",
            project_role="VIEWER",
            full_name="Viewer Ping",
        )
        issue = make_task(
            title="Mentionable issue",
            assignee="worker",
        )

        task = db_session.query(Task).filter(Task.id == issue["id"]).one()
        active_watchers = (
            db_session.query(Watcher)
            .filter(Watcher.task_id == task.id, Watcher.is_watching.is_(True))
            .all()
        )
        assert {item.user_id for item in active_watchers} == {seed["admin"].id, worker.id}

        as_user(seed["admin"])
        comment_response = client.post(
            f"/api/v1/issues/{issue['id']}/comments",
            json={"content": "Please review this flow, @viewer_ping"},
        )
        assert comment_response.status_code == 201, comment_response.text

        watchers_response = client.get(f"/api/v1/issues/{issue['id']}/watchers")
        assert watchers_response.status_code == 200
        watcher_ids = {item["id"] for item in watchers_response.json()["watchers"]}
        assert watcher_ids == {seed["admin"].id, worker.id, viewer.id}

        worker_notifications = (
            db_session.query(Notification)
            .filter(Notification.recipient_id == worker.id)
            .order_by(Notification.id.asc())
            .all()
        )
        viewer_notifications = (
            db_session.query(Notification)
            .filter(Notification.recipient_id == viewer.id)
            .order_by(Notification.id.asc())
            .all()
        )
        assert any(item.type == "issue_assigned" for item in worker_notifications)
        assert any(item.type == "issue_commented" for item in worker_notifications)
        assert [item.type for item in viewer_notifications] == ["issue_mentioned"]

    def test_duplicate_notification_dedupe_prevents_second_insert(self, client, db_session, make_task):
        seed = seed_test_hierarchy(db_session)
        worker = seed["worker"]
        issue = make_task(title="Dedupe issue")
        task = db_session.query(Task).filter(Task.id == issue["id"]).one()

        task.version += 1
        NotificationService.notify_issue_assigned(
            db_session, issue=task, actor_id=seed["admin"].id, assignee_id=worker.id
        )
        NotificationService.notify_issue_assigned(
            db_session, issue=task, actor_id=seed["admin"].id, assignee_id=worker.id
        )
        db_session.commit()

        count = (
            db_session.query(Notification)
            .filter(
                Notification.recipient_id == worker.id,
                Notification.type == "issue_assigned",
                Notification.issue_id == issue["id"],
            )
            .count()
        )
        assert count == 1

    def test_notification_generation_failure_does_not_fail_issue_update(
        self, client, make_task, monkeypatch
    ):
        issue = make_task(title="Failure-tolerant issue")

        def blow_up(*args, **kwargs):
            raise RuntimeError("notification insert failed")

        monkeypatch.setattr(NotificationService, "_create_notification", blow_up)

        response = client.patch(
            f"/api/v1/issues/{issue['id']}",
            json={"assignee_id": client.seed["worker"].id, "expected_version": issue["version"]},
        )

        assert response.status_code == 200, response.text
        assert response.json()["assignee_id"] == client.seed["worker"].id

    def test_status_and_blocked_notifications_skip_users_without_project_access(
        self, client, db_session, make_task, as_user
    ):
        seed = seed_test_hierarchy(db_session)
        outsider = _make_project_user(
            db_session, seed=seed, username="outsider_user", project_role=None
        )
        issue = make_task(title="Access safe issue", assignee="worker")
        task = db_session.query(Task).filter(Task.id == issue["id"]).one()

        NotificationService.notify_watcher_added(
            db_session,
            issue=task,
            actor_id=seed["admin"].id,
            recipient_id=outsider.id,
        )
        db_session.commit()
        assert (
            db_session.query(Notification)
            .filter(Notification.recipient_id == outsider.id)
            .count()
            == 0
        )

        as_user(seed["admin"])
        response = client.patch(
            f"/api/v1/issues/{issue['id']}",
            json={
                "is_blocked": True,
                "blocked_reason": "Waiting for compliance sign-off",
                "expected_version": issue["version"],
            },
        )

        assert response.status_code == 200, response.text
        outsider_count = (
            db_session.query(Notification)
            .filter(Notification.recipient_id == outsider.id)
            .count()
        )
        assert outsider_count == 0
