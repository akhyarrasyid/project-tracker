from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.notification import (
    NotificationBulkMarkReadResponse,
    NotificationFilter,
    NotificationListResponse,
    NotificationUnreadCountResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", summary="List notifications")
def list_notifications(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    filter: Annotated[NotificationFilter, Query()] = NotificationFilter.ALL,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    project_id: Annotated[int | None, Query()] = None,
) -> NotificationListResponse:
    return NotificationService.list_notifications(
        db,
        current_user=current_user,
        filter_by=filter,
        cursor=cursor,
        limit=limit,
        project_id=project_id,
    )


@router.get(
    "/unread-count",
    summary="Get unread notification count",
)
def get_unread_notification_count(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: Annotated[int | None, Query()] = None,
) -> NotificationUnreadCountResponse:
    return NotificationUnreadCountResponse(
        unread_count=NotificationService.unread_count(
            db, current_user=current_user, project_id=project_id
        )
    )


@router.patch(
    "/{notification_id}/read",
    summary="Mark a notification as read",
)
def mark_notification_read(
    notification_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    notification = NotificationService.mark_read(
        db, current_user=current_user, notification_id=notification_id
    )
    return {"notification": NotificationService.serialize_notification(notification)}


@router.patch(
    "/{notification_id}/unread",
    summary="Mark a notification as unread",
)
def mark_notification_unread(
    notification_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    notification = NotificationService.mark_unread(
        db, current_user=current_user, notification_id=notification_id
    )
    return {"notification": NotificationService.serialize_notification(notification)}


@router.post(
    "/mark-all-read",
    summary="Mark all notifications as read",
)
def mark_all_notifications_read(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NotificationBulkMarkReadResponse:
    return NotificationBulkMarkReadResponse(
        updated_count=NotificationService.mark_all_read(db, current_user=current_user)
    )
