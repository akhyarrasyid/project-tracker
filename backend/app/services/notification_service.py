import datetime
import logging
import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, exists, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.comment import Comment
from app.db.models.notification import Notification
from app.db.models.project_member import ProjectMember
from app.db.models.task import Task
from app.db.models.user import User
from app.db.models.watcher import Watcher
from app.schemas.issue import IssueUserSummary
from app.schemas.notification import (
    NotificationFilter,
    NotificationIssueSummary,
    NotificationListResponse,
    NotificationProjectSummary,
    NotificationResponse,
    NotificationType,
    WatcherSummary,
    decode_notification_cursor,
    encode_notification_cursor,
)
from app.services.watcher_service import WatcherService

logger = logging.getLogger(__name__)
MENTION_PATTERN = re.compile(r"@([A-Za-z0-9_][A-Za-z0-9_.-]{0,63})")
WATCHING_FILTER_TYPES = {
    NotificationType.ISSUE_COMMENTED,
    NotificationType.ISSUE_STATUS_CHANGED,
    NotificationType.ISSUE_BLOCKED,
    NotificationType.ISSUE_UNBLOCKED,
    NotificationType.WATCHER_ADDED,
}


class NotificationService:
    @staticmethod
    def _recipient_has_project_access(db: Session, recipient_id: int, project_id: int | None) -> bool:
        if project_id is None:
            return True

        user = db.query(User).filter(User.id == recipient_id, User.deleted_at.is_(None)).one_or_none()
        if user is None:
            return False
        if user.role == "admin":
            return True
        membership = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == recipient_id,
            )
            .one_or_none()
        )
        return membership is not None

    @staticmethod
    def _create_notification(
        db: Session,
        *,
        recipient_id: int,
        actor_id: int | None,
        issue: Task | None,
        notification_type: NotificationType,
        title: str,
        body_preview: str | None,
        metadata: dict[str, Any] | None = None,
        dedupe_key: str | None = None,
    ) -> Notification | None:
        if actor_id is not None and actor_id == recipient_id:
            return None

        project_id = issue.project_id if issue is not None else None
        if not NotificationService._recipient_has_project_access(db, recipient_id, project_id):
            return None

        notification = Notification(
            recipient_id=recipient_id,
            actor_id=actor_id,
            issue_id=issue.id if issue is not None else None,
            project_id=project_id,
            type=notification_type.value,
            title=title,
            body_preview=body_preview,
            metadata_json=metadata or {},
            dedupe_key=dedupe_key,
        )

        savepoint = db.begin_nested()
        try:
            db.add(notification)
            db.flush()
            savepoint.commit()
            return notification
        except IntegrityError:
            savepoint.rollback()
            logger.info("Skipped duplicate notification dedupe_key=%s", dedupe_key)
            return None
        except Exception:
            savepoint.rollback()
            logger.exception("Notification generation failed for recipient=%s", recipient_id)
            return None

    @staticmethod
    def _active_watcher_ids(db: Session, issue_id: int) -> set[int]:
        rows = (
            db.query(Watcher.user_id)
            .filter(Watcher.task_id == issue_id, Watcher.is_watching.is_(True))
            .all()
        )
        return {row[0] for row in rows}

    @staticmethod
    def _username_mentions(db: Session, content: str, issue: Task) -> dict[int, User]:
        usernames = {match.group(1) for match in MENTION_PATTERN.finditer(content)}
        if not usernames:
            return {}

        users = (
            db.query(User)
            .join(
                ProjectMember,
                and_(
                    ProjectMember.user_id == User.id,
                    ProjectMember.project_id == issue.project_id,
                ),
                isouter=True,
            )
            .filter(User.username.in_(usernames), User.deleted_at.is_(None), User.is_active.is_(True))
            .all()
        )
        result: dict[int, User] = {}
        for user in users:
            if user.role == "admin" or any(member.project_id == issue.project_id for member in getattr(user, "project_members", []) or []):
                result[user.id] = user
                continue
            membership = (
                db.query(ProjectMember)
                .filter(ProjectMember.project_id == issue.project_id, ProjectMember.user_id == user.id)
                .one_or_none()
            )
            if membership is not None:
                result[user.id] = user
        return result

    @staticmethod
    def serialize_notification(notification: Notification) -> NotificationResponse:
        actor = None
        if notification.actor is not None:
            actor = IssueUserSummary.model_validate(notification.actor)

        issue_summary = None
        if notification.issue is not None:
            issue_summary = NotificationIssueSummary(
                id=notification.issue.id,
                key=notification.issue.key,
                title=notification.issue.title,
            )

        project_summary = None
        if notification.project is not None:
            project_summary = NotificationProjectSummary.model_validate(notification.project)

        route_target = None
        if issue_summary and issue_summary.key:
            route_target = f"/issues/{issue_summary.key}"

        return NotificationResponse(
            id=notification.id,
            type=NotificationType(notification.type),
            title=notification.title,
            body_preview=notification.body_preview,
            metadata=notification.metadata_json or {},
            is_read=notification.is_read,
            read_at=notification.read_at,
            created_at=notification.created_at,
            actor=actor,
            issue=issue_summary,
            project=project_summary,
            route_target=route_target,
        )

    @staticmethod
    def list_notifications(
        db: Session,
        *,
        current_user: User,
        filter_by: NotificationFilter,
        cursor: str | None,
        limit: int,
        project_id: int | None = None,
    ) -> NotificationListResponse:
        query = db.query(Notification).filter(Notification.recipient_id == current_user.id)
        if current_user.role != "admin":
            query = query.filter(
                or_(
                    Notification.project_id.is_(None),
                    exists().where(
                        and_(
                            ProjectMember.project_id == Notification.project_id,
                            ProjectMember.user_id == current_user.id,
                        )
                    ),
                )
            )

        if project_id is not None:
            query = query.filter(Notification.project_id == project_id)
        if filter_by == NotificationFilter.UNREAD:
            query = query.filter(Notification.is_read.is_(False))
        elif filter_by == NotificationFilter.ASSIGNED:
            query = query.filter(Notification.type == NotificationType.ISSUE_ASSIGNED.value)
        elif filter_by == NotificationFilter.MENTIONS:
            query = query.filter(Notification.type == NotificationType.ISSUE_MENTIONED.value)
        elif filter_by == NotificationFilter.WATCHING:
            query = query.filter(
                Notification.type.in_([notification_type.value for notification_type in WATCHING_FILTER_TYPES])
            )

        if cursor:
            cursor_payload = decode_notification_cursor(cursor)
            query = query.filter(
                or_(
                    Notification.created_at < cursor_payload.created_at,
                    and_(
                        Notification.created_at == cursor_payload.created_at,
                        Notification.id < cursor_payload.notification_id,
                    ),
                )
            )

        rows = (
            query.order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit + 1)
            .all()
        )
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = encode_notification_cursor(last.created_at, last.id)
            rows = rows[:limit]
        return NotificationListResponse(
            items=[NotificationService.serialize_notification(row) for row in rows],
            next_cursor=next_cursor,
        )

    @staticmethod
    def unread_count(db: Session, *, current_user: User, project_id: int | None = None) -> int:
        query = db.query(Notification).filter(
            Notification.recipient_id == current_user.id,
            Notification.is_read.is_(False),
        )
        if current_user.role != "admin":
            query = query.filter(
                or_(
                    Notification.project_id.is_(None),
                    exists().where(
                        and_(
                            ProjectMember.project_id == Notification.project_id,
                            ProjectMember.user_id == current_user.id,
                        )
                    ),
                )
            )
        if project_id is not None:
            query = query.filter(Notification.project_id == project_id)
        return query.count()

    @staticmethod
    def get_owned_notification(db: Session, *, current_user: User, notification_id: int) -> Notification:
        notification = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.recipient_id == current_user.id)
            .one_or_none()
        )
        if notification is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )
        if (
            current_user.role != "admin"
            and notification.project_id is not None
            and not NotificationService._recipient_has_project_access(
                db, current_user.id, notification.project_id
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )
        return notification

    @staticmethod
    def mark_read(db: Session, *, current_user: User, notification_id: int) -> Notification:
        notification = NotificationService.get_owned_notification(
            db, current_user=current_user, notification_id=notification_id
        )
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            db.refresh(notification)
        return notification

    @staticmethod
    def mark_unread(db: Session, *, current_user: User, notification_id: int) -> Notification:
        notification = NotificationService.get_owned_notification(
            db, current_user=current_user, notification_id=notification_id
        )
        if notification.is_read:
            notification.is_read = False
            notification.read_at = None
            db.commit()
            db.refresh(notification)
        return notification

    @staticmethod
    def mark_all_read(db: Session, *, current_user: User) -> int:
        notifications = (
            db.query(Notification)
            .filter(Notification.recipient_id == current_user.id, Notification.is_read.is_(False))
            .all()
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        changed = 0
        for notification in notifications:
            if (
                notification.project_id is not None
                and current_user.role != "admin"
                and not NotificationService._recipient_has_project_access(
                    db, current_user.id, notification.project_id
                )
            ):
                continue
            notification.is_read = True
            notification.read_at = now
            changed += 1
        if changed:
            db.commit()
        return changed

    @staticmethod
    def build_watchers_payload(
        db: Session,
        *,
        issue: Task,
        current_user: User,
        can_manage_watchers: bool,
    ) -> dict[str, Any]:
        watchers = WatcherService.list_active_watchers(db, issue.id)
        return {
            "issue_id": issue.id,
            "count": len(watchers),
            "is_watching": any(item.user_id == current_user.id for item in watchers),
            "can_manage_watchers": can_manage_watchers,
            "watchers": [
                WatcherSummary.model_validate(item.user)
                for item in watchers
            ],
        }

    @staticmethod
    def notify_issue_assigned(
        db: Session,
        *,
        issue: Task,
        actor_id: int,
        assignee_id: int,
    ) -> None:
        try:
            actor = db.query(User).filter(User.id == actor_id).one_or_none()
            actor_name = actor.full_name if actor is not None else "System"
            NotificationService._create_notification(
                db,
                recipient_id=assignee_id,
                actor_id=actor_id,
                issue=issue,
                notification_type=NotificationType.ISSUE_ASSIGNED,
                title=f"{actor_name} assigned you to {issue.key}",
                body_preview=issue.title,
                metadata={"route_target": f"/issues/{issue.key}"},
                dedupe_key=f"issue:{issue.id}:assigned:user:{assignee_id}:version:{issue.version}",
            )
        except Exception:
            logger.exception("Failed to generate assignment notification for issue=%s", issue.id)

    @staticmethod
    def notify_watcher_added(
        db: Session,
        *,
        issue: Task,
        actor_id: int,
        recipient_id: int,
    ) -> None:
        try:
            actor = db.query(User).filter(User.id == actor_id).one_or_none()
            actor_name = actor.full_name if actor is not None else "System"
            NotificationService._create_notification(
                db,
                recipient_id=recipient_id,
                actor_id=actor_id,
                issue=issue,
                notification_type=NotificationType.WATCHER_ADDED,
                title=f"{actor_name} added you as a watcher on {issue.key}",
                body_preview=issue.title,
                metadata={"route_target": f"/issues/{issue.key}"},
                dedupe_key=f"issue:{issue.id}:watcher-added:user:{recipient_id}:version:{issue.version}",
            )
        except Exception:
            logger.exception("Failed to generate watcher-added notification for issue=%s", issue.id)

    @staticmethod
    def notify_issue_comment(
        db: Session,
        *,
        issue: Task,
        actor_id: int,
        comment: Comment,
    ) -> None:
        try:
            watcher_ids = NotificationService._active_watcher_ids(db, issue.id)
            if issue.assignee_id is not None:
                watcher_ids.add(issue.assignee_id)

            mentioned_users = NotificationService._username_mentions(db, comment.content, issue)
            mentioned_ids = set(mentioned_users)

            WatcherService.ensure_watcher(
                db,
                issue_id=issue.id,
                user_id=actor_id,
                actor_id=actor_id,
                auto=True,
            )
            for user_id in mentioned_ids:
                WatcherService.ensure_watcher(
                    db,
                    issue_id=issue.id,
                    user_id=user_id,
                    actor_id=actor_id,
                    auto=True,
                )

            actor = db.query(User).filter(User.id == actor_id).one_or_none()
            actor_name = actor.full_name if actor is not None else "System"
            preview = comment.content[:140]

            for recipient_id in mentioned_users:
                NotificationService._create_notification(
                    db,
                    recipient_id=recipient_id,
                    actor_id=actor_id,
                    issue=issue,
                    notification_type=NotificationType.ISSUE_MENTIONED,
                    title=f"{actor_name} mentioned you in {issue.key}",
                    body_preview=preview,
                    metadata={"comment_id": comment.id, "route_target": f"/issues/{issue.key}"},
                    dedupe_key=f"issue:{issue.id}:comment:{comment.id}:recipient:{recipient_id}:mention",
                )

            for recipient_id in watcher_ids - mentioned_ids:
                NotificationService._create_notification(
                    db,
                    recipient_id=recipient_id,
                    actor_id=actor_id,
                    issue=issue,
                    notification_type=NotificationType.ISSUE_COMMENTED,
                    title=f"{actor_name} commented on {issue.key}",
                    body_preview=preview,
                    metadata={"comment_id": comment.id, "route_target": f"/issues/{issue.key}"},
                    dedupe_key=f"issue:{issue.id}:comment:{comment.id}:recipient:{recipient_id}",
                )
        except Exception:
            logger.exception("Failed to generate comment notifications for issue=%s", issue.id)

    @staticmethod
    def notify_issue_updated(
        db: Session,
        *,
        issue: Task,
        actor_id: int,
        changes: dict[str, tuple[Any, Any]],
    ) -> None:
        try:
            watcher_ids = NotificationService._active_watcher_ids(db, issue.id)
            actor = db.query(User).filter(User.id == actor_id).one_or_none()
            actor_name = actor.full_name if actor is not None else "System"

            if "assignee_id" in changes and issue.assignee_id is not None:
                WatcherService.ensure_watcher(
                    db,
                    issue_id=issue.id,
                    user_id=issue.assignee_id,
                    actor_id=actor_id,
                    auto=True,
                )
                NotificationService.notify_issue_assigned(
                    db,
                    issue=issue,
                    actor_id=actor_id,
                    assignee_id=issue.assignee_id,
                )

            if "status" in changes:
                old_status, new_status = changes["status"]
                for recipient_id in watcher_ids:
                    NotificationService._create_notification(
                        db,
                        recipient_id=recipient_id,
                        actor_id=actor_id,
                        issue=issue,
                        notification_type=NotificationType.ISSUE_STATUS_CHANGED,
                        title=f"{issue.key} moved from {old_status} to {new_status}",
                        body_preview=issue.title,
                        metadata={"route_target": f"/issues/{issue.key}"},
                        dedupe_key=(
                            f"issue:{issue.id}:status:{new_status}:recipient:{recipient_id}:version:{issue.version}"
                        ),
                    )

            if "is_blocked" in changes:
                _old_blocked, new_blocked = changes["is_blocked"]
                recipients = set(watcher_ids)
                if issue.assignee_id is not None:
                    recipients.add(issue.assignee_id)
                for recipient_id in recipients:
                    notification_type = (
                        NotificationType.ISSUE_BLOCKED
                        if new_blocked
                        else NotificationType.ISSUE_UNBLOCKED
                    )
                    reason_preview = issue.blocked_reason if new_blocked else None
                    title = (
                        f"{issue.key} was blocked"
                        if new_blocked
                        else f"{issue.key} was unblocked"
                    )
                    NotificationService._create_notification(
                        db,
                        recipient_id=recipient_id,
                        actor_id=actor_id,
                        issue=issue,
                        notification_type=notification_type,
                        title=title,
                        body_preview=reason_preview or issue.title,
                        metadata={"route_target": f"/issues/{issue.key}", "actor_name": actor_name},
                        dedupe_key=(
                            f"issue:{issue.id}:{notification_type.value}:recipient:{recipient_id}:version:{issue.version}"
                        ),
                    )
        except Exception:
            logger.exception("Failed to generate update notifications for issue=%s", issue.id)
