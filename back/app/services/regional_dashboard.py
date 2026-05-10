from datetime import datetime, timezone

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
    CcaaKpis,
    ClientExecution,
    ExecutionKpis,
    ManagerPerformance,
    RegionSummary,
    RegionalDashboardResponse,
    Underperformer,
)

# Maps INE 2-digit numeric codes (used on the map SVG) to the Spanish CCAA
# names stored in clients.comunidad_autonoma. Must stay in sync with
# PROVINCIA_TO_CCAA in IA/generate_alerts.py.
_INE_COD_TO_CCAA: dict[str, str] = {
    "01": "Andalucía",
    "02": "Aragón",
    "03": "Asturias",
    "04": "Illes Balears",
    "05": "Canarias",
    "06": "Cantabria",
    "07": "Castilla y León",
    "08": "Castilla-La Mancha",
    "09": "Cataluña",
    "10": "Comunitat Valenciana",
    "11": "Extremadura",
    "12": "Galicia",
    "13": "Comunidad de Madrid",
    "14": "Región de Murcia",
    "15": "Navarra",
    "16": "País Vasco",
    "17": "La Rioja",
}

# Reverse: Spanish CCAA name → INE code (used to key ccaaKpis by client's CCAA)
_CCAA_TO_INE: dict[str, str] = {v: k for k, v in _INE_COD_TO_CCAA.items()}


async def get_regional_dashboard(session: AsyncSession, ccaa_filter: str | None = None) -> RegionalDashboardResponse:
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

    if ccaa_filter:
        # Translate INE numeric code → Spanish CCAA name stored in clients table.
        # This correctly handles provinces like Galicia (cod=12) whose clients
        # are served by agents from other provinces in the same zone.
        ccaa_name = _INE_COD_TO_CCAA.get(ccaa_filter)
        if ccaa_name:
            clients = [c for c in clients if c.comunidad_autonoma == ccaa_name]
        else:
            # Fallback: if code not in dict, try matching agent cod_ccaa directly.
            filtered_agent_ids = {a.id for a in agents if a.cod_ccaa == ccaa_filter}
            clients = [c for c in clients if c.agent_id in filtered_agent_ids]

    alerts_by_client = _group_by(alerts, "client_id")
    clients_by_agent = _group_by(clients, "agent_id")
    agents_by_manager = _group_by(agents, "manager_id")
    managers_by_region = _group_by(managers, "region_id")
    all_alerts: list[RegionalAlert] = []
    region_summaries: list[RegionSummary] = []
    underperformers: list[Underperformer] = []

    for region in regions:
        region_alerts: list[RegionalAlert] = []
        alerts_by_ccaa: dict[str, list[RegionalAlert]] = {}
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
                    # Group by client's actual CCAA (matches ccaa_filter behaviour)
                    ine_cod = _CCAA_TO_INE.get(client.comunidad_autonoma or "")
                    if ine_cod:
                        alerts_by_ccaa.setdefault(ine_cod, []).extend(client_alerts)

                agent_kpis = _calculate_kpis(agent_alerts)
                agent_summaries.append(
                    AgentPerformance(
                        id=agent.id,
                        name=agent.name,
                        email=agent.email,
                        cod_ccaa=agent.cod_ccaa,
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
        ccaa_kpis_list = [
            CcaaKpis(cod_ccaa=cod, kpis=_calculate_kpis(alerts))
            for cod, alerts in alerts_by_ccaa.items()
        ]
        region_summaries.append(
            RegionSummary(
                id=region.id,
                slug=region.slug,
                name=region.name,
                kpis=_calculate_kpis(region_alerts),
                managers=manager_summaries,
                ccaa_kpis=ccaa_kpis_list,
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


def _as_utc(dt: datetime) -> datetime:
    """Return a timezone-aware UTC datetime regardless of whether dt has tzinfo."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _calculate_kpis(alerts: list[RegionalAlert]) -> ExecutionKpis:
    total_alerts = len(alerts)
    pending_alerts = sum(1 for alert in alerts if alert.status == "pending")
    attended_alerts = sum(1 for alert in alerts if alert.status == "attended")
    dismissed_alerts = sum(1 for alert in alerts if alert.status == "dismissed")
    high_risk_backlog = sum(
        1 for alert in alerts if alert.status == "pending" and alert.risk_level == "high"
    )
    now = datetime.now(timezone.utc)
    overdue_followups = sum(
        1 for alert in alerts if alert.status == "pending" and _as_utc(alert.due_at) < now
    )
    response_hours = [
        (_as_utc(alert.attended_at) - _as_utc(alert.created_at)).total_seconds() / 3600
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
