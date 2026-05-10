from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.user import User
from app.schemas.notification import NotificationOut
from app.services.auth import get_current_user
from app.services.notification import (
    get_notifications_for_user,
    mark_all_read,
    mark_notification_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=list[NotificationOut])
async def list_notifications(session: SessionDep, current_user: CurrentUserDep) -> list:
    return await get_notifications_for_user(session, current_user.id)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
async def read_notification(
    notification_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> object:
    notif = await mark_notification_read(session, notification_id, current_user.id)
    if notif is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notif


@router.patch("/read-all", response_model=dict)
async def read_all_notifications(session: SessionDep, current_user: CurrentUserDep) -> dict:
    count = await mark_all_read(session, current_user.id)
    return {"marked_read": count}
