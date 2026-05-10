from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal as async_session_factory
from app.models.notification import Notification
from app.models.regional_dashboard import Client, RegionalAlert, SalesAgent

logger = logging.getLogger(__name__)

_HIGH_RISK_THRESHOLD_DAYS = 0


async def get_notifications_for_agent(session: AsyncSession, agent_id: int) -> list[Notification]:
    result = await session.execute(
        select(Notification)
        .where(Notification.agent_id == agent_id)
        .order_by(Notification.read_at.is_(None).desc(), Notification.created_at.desc())
    )
    return list(result.scalars().all())


async def mark_notification_read(session: AsyncSession, notification_id: int, agent_id: int) -> Notification | None:
    notif = await session.get(Notification, notification_id)
    if notif is None or notif.agent_id != agent_id:
        return None
    if notif.read_at is None:
        notif.read_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(notif)
    return notif


async def mark_all_read(session: AsyncSession, agent_id: int) -> int:
    result = await session.execute(
        select(Notification).where(
            and_(Notification.agent_id == agent_id, Notification.read_at.is_(None))
        )
    )
    unread = list(result.scalars().all())
    now = datetime.now(UTC)
    for n in unread:
        n.read_at = now
    await session.commit()
    return len(unread)


async def _already_notified_today(session: AsyncSession, agent_id: int, alert_id: str) -> bool:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.count()).where(
            and_(
                Notification.agent_id == agent_id,
                Notification.alert_id == alert_id,
                Notification.created_at >= today_start,
            )
        )
    )
    return (result.scalar() or 0) > 0


async def run_daily_notifications() -> None:
    """Creates reminder notifications for high-priority unresolved alerts older than 2 days.
    Scoped per sales agent using real DB data."""
    threshold = datetime.now(UTC) - timedelta(days=_HIGH_RISK_THRESHOLD_DAYS)

    async with async_session_factory() as session:
        result = await session.execute(
            select(RegionalAlert, Client, SalesAgent)
            .join(Client, RegionalAlert.client_id == Client.id)
            .join(SalesAgent, Client.agent_id == SalesAgent.id)
            .where(
                and_(
                    RegionalAlert.status == "pending",
                    RegionalAlert.risk_level == "high",
                    RegionalAlert.created_at <= threshold,
                )
            )
        )
        rows = result.all()

        if not rows:
            return

        for alert, client, agent in rows:
            alert_id_str = str(alert.id)
            if await _already_notified_today(session, agent.id, alert_id_str):
                continue

            days_old = (datetime.now(UTC) - alert.created_at.replace(tzinfo=UTC)).days
            notif = Notification(
                agent_id=agent.id,
                alert_id=alert_id_str,
                title=f"⚠️ Alerta prioritat alta: {client.name}",
                body=(
                    f"El client {client.name} porta {days_old} dies amb "
                    f"una alerta d'alt risc sense resoldre. Revisa i gestiona l'alerta."
                ),
            )
            session.add(notif)

        await session.commit()
        logger.info("Notification job completed: %d stale alerts processed", len(rows))
