from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal as async_session_factory
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger(__name__)

# Alerts that arrive via the static mock dataset use string IDs like "alert-1".
# The scheduler reads them from the mock data module so no DB table needed.
_HIGH_RISK_THRESHOLD_DAYS = 2


async def get_notifications_for_user(session: AsyncSession, user_id: int) -> list[Notification]:
    result = await session.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.read_at.is_(None).desc(), Notification.created_at.desc())
    )
    return list(result.scalars().all())


async def mark_notification_read(session: AsyncSession, notification_id: int, user_id: int) -> Notification | None:
    notif = await session.get(Notification, notification_id)
    if notif is None or notif.user_id != user_id:
        return None
    if notif.read_at is None:
        notif.read_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(notif)
    return notif


async def mark_all_read(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(Notification).where(
            and_(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
    )
    unread = list(result.scalars().all())
    now = datetime.now(UTC)
    for n in unread:
        n.read_at = now
    await session.commit()
    return len(unread)


async def _already_notified_today(session: AsyncSession, user_id: int, alert_id: str) -> bool:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.count()).where(
            and_(
                Notification.user_id == user_id,
                Notification.alert_id == alert_id,
                Notification.created_at >= today_start,
            )
        )
    )
    return (result.scalar() or 0) > 0


async def run_daily_notifications() -> None:
    """Called once per day. Creates reminder notifications for high-priority
    unresolved alerts older than 2 days."""
    from app.data.mock_alerts import get_pending_high_risk_alerts  # lazy import

    try:
        stale_alerts = get_pending_high_risk_alerts(min_days_old=_HIGH_RISK_THRESHOLD_DAYS)
    except Exception:
        logger.warning("Could not load mock alerts for notification scheduler")
        return

    if not stale_alerts:
        return

    async with async_session_factory() as session:
        users_result = await session.execute(select(User))
        users = list(users_result.scalars().all())

        for user in users:
            for alert in stale_alerts:
                if await _already_notified_today(session, user.id, alert["id"]):
                    continue
                days_old = alert["days_old"]
                notif = Notification(
                    user_id=user.id,
                    alert_id=alert["id"],
                    title=f"⚠️ Alerta prioritat alta: {alert['clientName']}",
                    body=(
                        f"El client {alert['clientName']} porta {days_old} dies amb "
                        f"una alerta d'alt risc sense resoldre. Revisa i gestiona l'alerta."
                    ),
                )
                session.add(notif)

        await session.commit()
        logger.info("Notification job completed: %d alerts, %d users", len(stale_alerts), len(users))
