from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from . import notification_db, security
from .notification_schemas import NotificationList, NotificationOut


router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


@router.get("", response_model=NotificationList)
def get_notifications(
    machine_id: Optional[str] = Query(default=None, min_length=1, max_length=64),
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(security.current_user),
):
    return notification_db.list_notifications(
        user_id=user["id"],
        machine_id=machine_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@router.get("/{notification_id}", response_model=NotificationOut)
def get_notification(
    notification_id: int,
    user: dict = Depends(security.current_user),
):
    notification = notification_db.get_notification(
        notification_id=notification_id,
        user_id=user["id"],
    )

    if notification is None:
        raise HTTPException(
            status_code=404,
            detail="Notification not found.",
        )

    return notification


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    user: dict = Depends(security.current_user),
):
    found = notification_db.mark_as_read(
        notification_id=notification_id,
        user_id=user["id"],
    )

    if not found:
        raise HTTPException(
            status_code=404,
            detail="Notification not found.",
        )

    return notification_db.get_notification(
        notification_id=notification_id,
        user_id=user["id"],
    )


@router.post("/{notification_id}/acknowledge", response_model=NotificationOut)
def acknowledge_notification(
    notification_id: int,
    admin: dict = Depends(security.require_admin),
):
    found = notification_db.acknowledge_notification(
        notification_id=notification_id,
        user_id=admin["id"],
        username=admin["username"],
    )

    if not found:
        raise HTTPException(
            status_code=404,
            detail="Notification not found.",
        )

    return notification_db.get_notification(
        notification_id=notification_id,
        user_id=admin["id"],
    )