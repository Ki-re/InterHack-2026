from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.regional_dashboard import RegionalDashboardResponse
from app.services.regional_dashboard import get_regional_dashboard

router = APIRouter(prefix="/regional-dashboard", tags=["regional-dashboard"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=RegionalDashboardResponse)
async def read_regional_dashboard(session: SessionDep) -> RegionalDashboardResponse:
    return await get_regional_dashboard(session)
