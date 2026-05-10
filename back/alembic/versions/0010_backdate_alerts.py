"""Backdate all regional_alerts to start of week (Mon 5-May to Wed 7-May 2026)
and reset all interaction/status columns so seed_demo.py re-seeds cleanly.

Revision ID: 0010_backdate_alerts
Revises: 0009_merge_heads
Create Date: 2026-05-10 09:00:00.000000

Why:
  All alerts were timestamped at migration time (today).  This migration
  spreads created_at deterministically over Mon–Wed of the current week so
  the demo looks realistic: alerts were raised early in the week, delegates
  worked them through the week (synthetic interactions), and a small backlog
  remains open as of today (Sunday).

  Resets interaction columns so seed_demo.py (run after every fresh
  container start) can re-seed a clean dataset that uses the new timestamps.
"""

import random
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from alembic import op

revision = "0010_backdate_alerts"
down_revision = "0009_merge_heads"
branch_labels = None
depends_on = None

# Window: Mon 5-May 2026 08:00 UTC  →  Wed 7-May 2026 18:00 UTC
_START = datetime(2026, 5, 5, 8, 0, 0, tzinfo=timezone.utc)
_END   = datetime(2026, 5, 7, 18, 0, 0, tzinfo=timezone.utc)
_DUE_OFFSET_DAYS = 5   # due_at = created_at + 5 days
_RNG_SEED = 7          # fixed seed → same timestamps on every fresh deploy


def upgrade() -> None:
    bind = op.get_bind()

    # Fetch all alert IDs in a stable order
    result = bind.execute(sa.text("SELECT id FROM regional_alerts ORDER BY id"))
    ids = [row[0] for row in result]

    if not ids:
        return

    window_secs = (_END - _START).total_seconds()
    rng = random.Random(_RNG_SEED)

    params = []
    for alert_id in ids:
        offset_secs = rng.uniform(0, window_secs)
        created_at = _START + timedelta(seconds=offset_secs)
        due_at = created_at + timedelta(days=_DUE_OFFSET_DAYS)
        params.append({
            "c": created_at.isoformat(),
            "d": due_at.isoformat(),
            "id": alert_id,
        })

    bind.execute(
        sa.text(
            """
            UPDATE regional_alerts
            SET created_at       = :c,
                due_at           = :d,
                status           = 'pending',
                attended_at      = NULL,
                dismissed_at     = NULL,
                dismiss_reason   = NULL,
                interactions_json = NULL,
                events_json      = NULL
            WHERE id = :id
            """
        ),
        params,
    )


def downgrade() -> None:
    # Non-reversible data migration — downgrade is a no-op
    pass
