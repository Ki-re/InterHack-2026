from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.alerts import SalesAlertResponse
from app.services.alerts import get_alerts

router = APIRouter(prefix="/alerts", tags=["alerts"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[SalesAlertResponse])
async def read_alerts(
    session: SessionDep,
    agent_id: int | None = Query(default=None, description="Filter alerts by sales agent ID"),
) -> list[SalesAlertResponse]:
    return await get_alerts(session, agent_id=agent_id)

