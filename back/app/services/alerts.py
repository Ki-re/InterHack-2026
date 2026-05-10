import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.regional_dashboard import Client, RegionalAlert
from app.schemas.alerts import SalesAlertResponse

_RISK_TO_FRONTEND = {"high": "high", "medium": "medium", "low": "low"}


async def get_alerts(
    session: AsyncSession,
    agent_id: int | None = None,
) -> list[SalesAlertResponse]:
    query = (
        select(RegionalAlert, Client)
        .join(Client, RegionalAlert.client_id == Client.id)
        .order_by(RegionalAlert.created_at.desc())
    )
    if agent_id is not None:
        query = query.where(Client.agent_id == agent_id)

    result = await session.execute(query)
    rows = result.all()

    alerts: list[SalesAlertResponse] = []
    for alert, client in rows:
        interactions = json.loads(alert.interactions_json) if alert.interactions_json else []
        events = json.loads(alert.events_json) if alert.events_json else []
        dismissed_at = (
            alert.dismissed_at.isoformat() if alert.dismissed_at else None
        )
        alerts.append(
            SalesAlertResponse(
                id=str(alert.id),
                clientName=client.name,
                riskLevel=_RISK_TO_FRONTEND.get(alert.risk_level, "medium"),
                churnProbability=alert.churn_probability,
                purchasePropensity=alert.purchase_propensity,
                customerValue=_RISK_TO_FRONTEND.get(client.customer_value, "medium"),
                explanation=alert.explanation or "",
                churnType=alert.churn_type or "Total",
                status=alert.status,
                interactions=interactions,
                events=events,
                dismissReason=alert.dismiss_reason,
                dismissedAt=dismissed_at,
                alertContextJson=alert.alert_context_json,
                predictedNextPurchase=alert.predicted_next_purchase,
                lastOrderDate=alert.last_order_date,
            )
        )
    return alerts

