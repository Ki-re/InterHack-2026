from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.regional_dashboard import (
    Client,
    Region,
    RegionalAlert,
    RegionalManager,
    SalesAgent,
)
from app.schemas.regional_dashboard import (
    AgentPerformance,
    AlertExecution,
    ClientExecution,
    ExecutionKpis,
    ManagerPerformance,
    RegionSummary,
    RegionalDashboardResponse,
    Underperformer,
)


async def get_regional_dashboard(session: AsyncSession) -> RegionalDashboardResponse:
    regions = list(
        (
            await session.execute(select(Region).order_by(Region.display_order, Region.id))
        )
        .scalars()
        .all()
    )
    managers = list(
        (await session.execute(select(RegionalManager).order_by(RegionalManager.id))).scalars().all()
    )
    agents = list((await session.execute(select(SalesAgent).order_by(SalesAgent.id))).scalars().all())
    clients = list((await session.execute(select(Client).order_by(Client.id))).scalars().all())
    alerts = list(
        (await session.execute(select(RegionalAlert).order_by(RegionalAlert.created_at))).scalars().all()
    )

    alerts_by_client = _group_by(alerts, "client_id")
    clients_by_agent = _group_by(clients, "agent_id")
    agents_by_manager = _group_by(agents, "manager_id")
    managers_by_region = _group_by(managers, "region_id")
    all_alerts: list[RegionalAlert] = []
    region_summaries: list[RegionSummary] = []
    underperformers: list[Underperformer] = []

    for region in regions:
        region_alerts: list[RegionalAlert] = []
        manager_summaries: list[ManagerPerformance] = []

        for manager in managers_by_region.get(region.id, []):
            manager_alerts: list[RegionalAlert] = []
            agent_summaries: list[AgentPerformance] = []

            for agent in agents_by_manager.get(manager.id, []):
                agent_alerts: list[RegionalAlert] = []
                client_summaries: list[ClientExecution] = []

                for client in clients_by_agent.get(agent.id, []):
                    client_alerts = alerts_by_client.get(client.id, [])
                    agent_alerts.extend(client_alerts)
                    client_summaries.append(_build_client(client, client_alerts))

                agent_kpis = _calculate_kpis(agent_alerts)
                agent_summaries.append(
                    AgentPerformance(
                        id=agent.id,
                        name=agent.name,
                        email=agent.email,
                        kpis=agent_kpis,
                        clients=client_summaries,
                    )
                )
                _append_underperformer(
                    underperformers,
                    level="agent",
                    id=agent.id,
                    name=agent.name,
                    parent_name=manager.name,
                    region_slug=region.slug,
                    kpis=agent_kpis,
                )
                manager_alerts.extend(agent_alerts)

            manager_kpis = _calculate_kpis(manager_alerts)
            manager_summaries.append(
                ManagerPerformance(
                    id=manager.id,
                    name=manager.name,
                    email=manager.email,
                    kpis=manager_kpis,
                    agents=agent_summaries,
                )
            )
            _append_underperformer(
                underperformers,
                level="manager",
                id=manager.id,
                name=manager.name,
                parent_name=None,
                region_slug=region.slug,
                kpis=manager_kpis,
            )
            region_alerts.extend(manager_alerts)

        all_alerts.extend(region_alerts)
        region_summaries.append(
            RegionSummary(
                id=region.id,
                slug=region.slug,
                name=region.name,
                kpis=_calculate_kpis(region_alerts),
                managers=manager_summaries,
            )
        )

    underperformers.sort(key=lambda item: (item.execution_score, -item.high_risk_backlog))

    return RegionalDashboardResponse(
        generated_at=datetime.utcnow(),
        kpis=_calculate_kpis(all_alerts),
        regions=region_summaries,
        underperformers=underperformers[:6],
    )


def _group_by(items: list, attribute: str) -> dict[int, list]:
    grouped: dict[int, list] = {}
    for item in items:
        grouped.setdefault(getattr(item, attribute), []).append(item)
    return grouped


def _build_client(client: Client, alerts: list[RegionalAlert]) -> ClientExecution:
    return ClientExecution(
        id=client.id,
        name=client.name,
        customer_value=client.customer_value,
        segment=client.segment,
        kpis=_calculate_kpis(alerts),
        alerts=[
            AlertExecution(
                id=alert.id,
                status=alert.status,
                risk_level=alert.risk_level,
                churn_probability=alert.churn_probability,
                purchase_propensity=alert.purchase_propensity,
                estimated_value=alert.estimated_value,
                created_at=alert.created_at,
                due_at=alert.due_at,
                attended_at=alert.attended_at,
                dismissed_at=alert.dismissed_at,
            )
            for alert in alerts
        ],
    )


def _calculate_kpis(alerts: list[RegionalAlert]) -> ExecutionKpis:
    total_alerts = len(alerts)
    pending_alerts = sum(1 for alert in alerts if alert.status == "pending")
    attended_alerts = sum(1 for alert in alerts if alert.status == "attended")
    dismissed_alerts = sum(1 for alert in alerts if alert.status == "dismissed")
    high_risk_backlog = sum(
        1 for alert in alerts if alert.status == "pending" and alert.risk_level == "high"
    )
    now = datetime.utcnow()
    overdue_followups = sum(
        1 for alert in alerts if alert.status == "pending" and alert.due_at < now
    )
    response_hours = [
        (alert.attended_at - alert.created_at).total_seconds() / 3600
        for alert in alerts
        if alert.status == "attended" and alert.attended_at is not None
    ]
    average_response_hours = (
        round(sum(response_hours) / len(response_hours), 1) if response_hours else None
    )
    attended_rate = round((attended_alerts / total_alerts) * 100) if total_alerts else 0
    dismissal_rate = round((dismissed_alerts / total_alerts) * 100) if total_alerts else 0
    overdue_penalty = round((overdue_followups / total_alerts) * 30) if total_alerts else 0
    high_risk_penalty = round((high_risk_backlog / total_alerts) * 25) if total_alerts else 0
    dismissal_penalty = round(dismissal_rate * 0.25)
    response_penalty = 0
    if average_response_hours is not None and average_response_hours > 30:
        response_penalty = min(12, round((average_response_hours - 30) / 6))
    execution_score = max(
        0,
        min(
            100,
            attended_rate - overdue_penalty - high_risk_penalty - dismissal_penalty - response_penalty,
        ),
    )

    if execution_score >= 75:
        status = "good"
    elif execution_score >= 55:
        status = "warning"
    else:
        status = "critical"

    return ExecutionKpis(
        total_alerts=total_alerts,
        pending_alerts=pending_alerts,
        attended_alerts=attended_alerts,
        dismissed_alerts=dismissed_alerts,
        attended_rate=attended_rate,
        dismissal_rate=dismissal_rate,
        high_risk_backlog=high_risk_backlog,
        overdue_followups=overdue_followups,
        average_response_hours=average_response_hours,
        execution_score=execution_score,
        status=status,
    )


def _append_underperformer(
    underperformers: list[Underperformer],
    *,
    level: str,
    id: int,
    name: str,
    parent_name: str | None,
    region_slug: str,
    kpis: ExecutionKpis,
) -> None:
    if kpis.status == "good" and kpis.high_risk_backlog == 0 and kpis.overdue_followups <= 1:
        return

    underperformers.append(
        Underperformer(
            level=level,
            id=id,
            name=name,
            parent_name=parent_name,
            region_slug=region_slug,
            execution_score=kpis.execution_score,
            pending_alerts=kpis.pending_alerts,
            high_risk_backlog=kpis.high_risk_backlog,
            overdue_followups=kpis.overdue_followups,
        )
    )
