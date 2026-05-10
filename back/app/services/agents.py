from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.regional_dashboard import Region, RegionalManager, SalesAgent
from app.schemas.agents import AgentResponse

_ZONE_FOR_REGION_SLUG = {
    "north": "north",
    "east": "east",
    "south": "south",
    "canary": "canary",
    "balearic": "balearic",
}


async def get_agents(session: AsyncSession) -> list[AgentResponse]:
    result = await session.execute(
        select(SalesAgent, RegionalManager, Region)
        .join(RegionalManager, SalesAgent.manager_id == RegionalManager.id)
        .join(Region, RegionalManager.region_id == Region.id)
        .order_by(SalesAgent.id)
    )
    rows = result.all()

    return [
        AgentResponse(
            id=agent.id,
            name=agent.name,
            email=agent.email,
            zone=_ZONE_FOR_REGION_SLUG.get(region.slug, region.slug),
            managerId=agent.manager_id,
        )
        for agent, manager, region in rows
    ]
