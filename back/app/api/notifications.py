from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.notification import NotificationOut
from app.services.notification import (
    get_notifications_for_agent,
    mark_all_read,
    mark_notification_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    session: Annotated[AsyncSession, Depends(get_session)],
    agent_id: int = Query(..., description="Sales agent ID"),
) -> list:
    return await get_notifications_for_agent(session, agent_id)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
async def read_notification(
    notification_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    agent_id: int = Query(..., description="Sales agent ID"),
) -> object:
    notif = await mark_notification_read(session, notification_id, agent_id)
    if notif is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notif


@router.patch("/read-all", response_model=dict)
async def read_all_notifications(
    session: Annotated[AsyncSession, Depends(get_session)],
    agent_id: int = Query(..., description="Sales agent ID"),
) -> dict:
    count = await mark_all_read(session, agent_id)
    return {"marked_read": count}
