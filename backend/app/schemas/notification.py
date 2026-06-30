import base64
import datetime
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.schemas.issue import IssueUserSummary
from app.schemas.task import _serialize_dt


class NotificationType(str, Enum):
    ISSUE_ASSIGNED = "issue_assigned"
    ISSUE_MENTIONED = "issue_mentioned"
    ISSUE_COMMENTED = "issue_commented"
    ISSUE_STATUS_CHANGED = "issue_status_changed"
    ISSUE_BLOCKED = "issue_blocked"
    ISSUE_UNBLOCKED = "issue_unblocked"
    WATCHER_ADDED = "watcher_added"
    LEGACY_EVENT = "legacy_event"


ACTION_BY_NOTIFICATION_TYPE: dict[str, str] = {
    NotificationType.ISSUE_ASSIGNED.value: "assigned",
    NotificationType.ISSUE_MENTIONED.value: "mentioned",
    NotificationType.ISSUE_COMMENTED.value: "commented",
    NotificationType.ISSUE_STATUS_CHANGED.value: "status_changed",
    NotificationType.ISSUE_BLOCKED.value: "blocked",
    NotificationType.ISSUE_UNBLOCKED.value: "unblocked",
    NotificationType.WATCHER_ADDED.value: "watcher_added",
    NotificationType.LEGACY_EVENT.value: "legacy_event",
}


def notification_action_for_type(notification_type: str | NotificationType) -> str:
    value = (
        notification_type.value
        if isinstance(notification_type, NotificationType)
        else notification_type
    )
    return ACTION_BY_NOTIFICATION_TYPE.get(value, "legacy_event")


class NotificationFilter(str, Enum):
    ALL = "all"
    UNREAD = "unread"
    ASSIGNED = "assigned"
    MENTIONS = "mentions"
    WATCHING = "watching"


class NotificationProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str


class NotificationIssueSummary(BaseModel):
    id: int | None = None
    key: str | None = None
    title: str | None = None


class NotificationResponse(BaseModel):
    id: int
    type: NotificationType
    title: str
    body_preview: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_read: bool
    read_at: datetime.datetime | None = None
    created_at: datetime.datetime
    actor: IssueUserSummary | None = None
    issue: NotificationIssueSummary | None = None
    project: NotificationProjectSummary | None = None
    route_target: str | None = None

    @field_serializer("created_at", "read_at")
    def serialize_dt(self, dt: datetime.datetime | None, _info) -> str | None:
        if dt is None:
            return None
        return _serialize_dt(dt)


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    next_cursor: str | None = None


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationBulkMarkReadResponse(BaseModel):
    updated_count: int


class WatcherSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str


class IssueWatchersResponse(BaseModel):
    issue_id: int
    count: int
    is_watching: bool
    can_manage_watchers: bool
    watchers: list[WatcherSummary]


class CursorPayload(BaseModel):
    created_at: datetime.datetime
    notification_id: int


def encode_notification_cursor(created_at: datetime.datetime, notification_id: int) -> str:
    payload = json.dumps(
        {
            "created_at": _serialize_dt(created_at),
            "notification_id": notification_id,
        }
    )
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_notification_cursor(cursor: str) -> CursorPayload:
    decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    raw = json.loads(decoded)
    return CursorPayload(
        created_at=datetime.datetime.fromisoformat(
            raw["created_at"].replace("Z", "+00:00")
        ),
        notification_id=raw["notification_id"],
    )
