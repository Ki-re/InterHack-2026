from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.agents import AgentResponse
from app.services.agents import get_agents

router = APIRouter(prefix="/agents", tags=["agents"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[AgentResponse])
async def read_agents(session: SessionDep) -> list[AgentResponse]:
    return await get_agents(session)
