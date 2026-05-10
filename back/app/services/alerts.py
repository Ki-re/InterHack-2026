from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.regional_dashboard import Client, RegionalAlert
from app.schemas.alerts import SalesAlertResponse

_RISK_TO_FRONTEND = {"high": "high", "medium": "medium", "low": "low"}


async def get_alerts(session: AsyncSession) -> list[SalesAlertResponse]:
    result = await session.execute(
        select(RegionalAlert, Client)
        .join(Client, RegionalAlert.client_id == Client.id)
        .order_by(RegionalAlert.created_at.desc())
    )
    rows = result.all()

    alerts: list[SalesAlertResponse] = []
    for alert, client in rows:
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
                interactions=[],
                events=[],
                alertContextJson=alert.alert_context_json,
                predictedNextPurchase=alert.predicted_next_purchase,
                lastOrderDate=alert.last_order_date,
            )
        )
    return alerts
