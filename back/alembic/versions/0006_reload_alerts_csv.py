"""reload alerts from regenerated CSV – rescaled scores & percentile risk levels

Revision ID: 0006_reload_alerts_csv
Revises: 0005_load_alerts_from_csv
Create Date: 2026-05-10 00:00:00.000000

This migration drops and re-inserts all clients and alerts from the current
alerts.csv (which now has percentile-normalised, rescaled churn_probability /
purchase_propensity and within-set percentile-based risk levels).
No schema changes – data reload only.
"""

import csv
import json
import os
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from alembic import op

revision = "0006_reload_alerts_csv"
down_revision = "0005_load_alerts_from_csv"
branch_labels = None
depends_on = None

CSV_PATH       = "/app/ia_data/alerts.csv"
CSV_PATH_LOCAL = os.path.join(os.path.dirname(__file__), "..", "..", "..", "IA", "alerts.csv")

RISK_MAP = {"Alto": "high", "Medio": "medium", "Bajo": "low"}


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. Clear existing alerts and clients (FK order) ───────────────────────
    bind.execute(sa.text("DELETE FROM regional_alerts"))
    bind.execute(sa.text("DELETE FROM clients"))

    # ── 2. Load CSV ───────────────────────────────────────────────────────────
    csv_path = CSV_PATH if os.path.exists(CSV_PATH) else CSV_PATH_LOCAL
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"alerts.csv not found at {CSV_PATH} or {CSV_PATH_LOCAL}. "
            "Ensure ./IA is mounted as /app/ia_data in docker-compose."
        )

    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    # ── 3. Re-insert clients ──────────────────────────────────────────────────
    clients_t = sa.table(
        "clients",
        sa.column("id"),
        sa.column("agent_id"),
        sa.column("name"),
        sa.column("customer_value"),
        sa.column("segment"),
        sa.column("provincia"),
        sa.column("comunidad_autonoma"),
        sa.column("zone"),
    )

    seen_csv_client_ids: dict[str, int] = {}
    client_rows = []
    db_client_id = 1
    for row in rows:
        csv_cid = row["client_id"]
        if csv_cid in seen_csv_client_ids:
            continue
        seen_csv_client_ids[csv_cid] = db_client_id
        client_rows.append({
            "id":               db_client_id,
            "agent_id":         int(row["agent_id"]),
            "name":             row["client_name"],
            "customer_value":   RISK_MAP.get(row["client_value"], "medium"),
            "segment":          row["zone"],
            "provincia":        row["provincia"],
            "comunidad_autonoma": row["comunidad_autonoma"],
            "zone":             row["zone"],
        })
        db_client_id += 1

    op.bulk_insert(clients_t, client_rows)

    # ── 4. Re-insert alerts ───────────────────────────────────────────────────
    alerts_t = sa.table(
        "regional_alerts",
        sa.column("id"),
        sa.column("client_id"),
        sa.column("status"),
        sa.column("risk_level"),
        sa.column("churn_probability"),
        sa.column("purchase_propensity"),
        sa.column("estimated_value"),
        sa.column("explanation"),
        sa.column("churn_type"),
        sa.column("predicted_next_purchase"),
        sa.column("last_order_date"),
        sa.column("alert_context_json"),
        sa.column("created_at"),
        sa.column("due_at"),
    )

    ctx_fields = [
        "ctx_productos_afectados", "ctx_n_productos", "ctx_gasto_anual_real",
        "ctx_gasto_esperado", "ctx_dias_desde_compra", "ctx_tiempo_medio_recompra",
        "ctx_zscore_momento", "ctx_potencial_clase", "ctx_num_compras_anteriores",
        "ctx_total_compras_otros", "ctx_vuelve_a_comprar",
        "inference_reference_date", "inference_window_start", "inference_window_end",
    ]

    now_utc = datetime.now(timezone.utc)
    alert_rows = []
    for alert_idx, row in enumerate(rows, start=1):
        db_cid = seen_csv_client_ids[row["client_id"]]

        due_at = now_utc + timedelta(days=30)
        pnp = row.get("predicted_next_purchase", "")
        if pnp:
            try:
                due_at = datetime.fromisoformat(pnp).replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        ctx = {k: row.get(k, "") for k in ctx_fields}

        alert_rows.append({
            "id":                    alert_idx,
            "client_id":             db_cid,
            "status":                "pending",
            "risk_level":            RISK_MAP.get(row["risk_level"], "medium"),
            "churn_probability":     round(float(row["churn_probability"])),
            "purchase_propensity":   round(float(row["purchase_propensity"])),
            "estimated_value":       float(row["alert_score"]),
            "explanation":           row.get("explanation", ""),
            "churn_type":            row.get("alert_type", ""),
            "predicted_next_purchase": pnp or None,
            "last_order_date":       row.get("last_order_date") or None,
            "alert_context_json":    json.dumps(ctx, ensure_ascii=False),
            "created_at":            now_utc,
            "due_at":                due_at,
        })

    op.bulk_insert(alerts_t, alert_rows)


def downgrade() -> None:
    # Nothing useful to downgrade to – simply clear the reloaded data
    op.get_bind().execute(sa.text("DELETE FROM regional_alerts"))
    op.get_bind().execute(sa.text("DELETE FROM clients"))
