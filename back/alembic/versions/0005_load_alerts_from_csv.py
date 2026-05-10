"""load alerts from CSV – replace mock seed data with real predictions

Revision ID: 0005_load_alerts_from_csv
Revises: 0004_create_notifications
Create Date: 2026-05-11 00:00:00.000000
"""

import csv
import json
import os
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from alembic import op

revision = "0005_load_alerts_from_csv"
down_revision = "0004_create_notifications"
branch_labels = None
depends_on = None

# Path where docker-compose mounts the IA/ directory
CSV_PATH = "/app/ia_data/alerts.csv"

# Fallback path for local runs outside Docker
CSV_PATH_LOCAL = os.path.join(os.path.dirname(__file__), "..", "..", "..", "IA", "alerts.csv")

RISK_MAP = {"Alto": "high", "Medio": "medium", "Bajo": "low"}

# ──────────────────────────────────────────────────────────────────
# Seed tables (reflect new 5-zone structure)
# ──────────────────────────────────────────────────────────────────
REGIONS = [
    {"id": 1, "slug": "north",    "name": "Nord",             "display_order": 1},
    {"id": 2, "slug": "east",     "name": "Est",              "display_order": 2},
    {"id": 3, "slug": "south",    "name": "Sud",              "display_order": 3},
    {"id": 4, "slug": "canary",   "name": "Illes Canàries",   "display_order": 4},
    {"id": 5, "slug": "balearic", "name": "Illes Balears",    "display_order": 5},
]

MANAGERS = [
    {"id": 1, "region_id": 1, "name": "Ane Etxebarria",  "email": "ane.etxebarria@inibsa.local"},
    {"id": 2, "region_id": 2, "name": "Marta Soler",     "email": "marta.soler@inibsa.local"},
    {"id": 3, "region_id": 3, "name": "Lucía Navarro",   "email": "lucia.navarro@inibsa.local"},
    {"id": 4, "region_id": 4, "name": "Elena Torres",    "email": "elena.torres@inibsa.local"},
    {"id": 5, "region_id": 5, "name": "Joan Ferrer",     "email": "joan.ferrer@inibsa.local"},
]

# agent_id matches CSV agent_id (1–13)
AGENTS = [
    # north (1-3) → manager 1
    {"id": 1,  "manager_id": 1, "name": "Iker Alonso",    "email": "iker.alonso@inibsa.local"},
    {"id": 2,  "manager_id": 1, "name": "Leire Martín",   "email": "leire.martin@inibsa.local"},
    {"id": 3,  "manager_id": 1, "name": "Jordi Roca",     "email": "jordi.roca@inibsa.local"},
    # east (4-6) → manager 2
    {"id": 4,  "manager_id": 2, "name": "Clara Puig",     "email": "clara.puig@inibsa.local"},
    {"id": 5,  "manager_id": 2, "name": "Marc Vidal",     "email": "marc.vidal@inibsa.local"},
    {"id": 6,  "manager_id": 2, "name": "Nuria Costa",    "email": "nuria.costa@inibsa.local"},
    # south (7-9) → manager 3
    {"id": 7,  "manager_id": 3, "name": "Sofía Prieto",   "email": "sofia.prieto@inibsa.local"},
    {"id": 8,  "manager_id": 3, "name": "Hugo Campos",    "email": "hugo.campos@inibsa.local"},
    {"id": 9,  "manager_id": 3, "name": "Carmen Vega",    "email": "carmen.vega@inibsa.local"},
    # canary (10-12) → manager 4
    {"id": 10, "manager_id": 4, "name": "Carlos Sánchez", "email": "carlos.sanchez@inibsa.local"},
    {"id": 11, "manager_id": 4, "name": "Ana Lima",       "email": "ana.lima@inibsa.local"},
    {"id": 12, "manager_id": 4, "name": "Pedro Reyes",    "email": "pedro.reyes@inibsa.local"},
    # balearic (13) → manager 5
    {"id": 13, "manager_id": 5, "name": "Laura Moll",     "email": "laura.moll@inibsa.local"},
]


def upgrade() -> None:
    # ── 1. Add new columns to regional_alerts ────────────────────
    op.add_column("regional_alerts", sa.Column("explanation", sa.Text(), nullable=True))
    op.add_column("regional_alerts", sa.Column("churn_type", sa.String(length=40), nullable=True))
    op.add_column("regional_alerts", sa.Column("dismiss_reason", sa.Text(), nullable=True))
    op.add_column("regional_alerts", sa.Column("predicted_next_purchase", sa.String(length=20), nullable=True))
    op.add_column("regional_alerts", sa.Column("last_order_date", sa.String(length=20), nullable=True))
    op.add_column("regional_alerts", sa.Column("alert_context_json", sa.Text(), nullable=True))

    # ── 2. Add new columns to clients ────────────────────────────
    op.add_column("clients", sa.Column("provincia", sa.String(length=80), nullable=True))
    op.add_column("clients", sa.Column("comunidad_autonoma", sa.String(length=80), nullable=True))
    op.add_column("clients", sa.Column("zone", sa.String(length=20), nullable=True))

    # ── 3. Clear old mock seed data (FK order) ───────────────────
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM regional_alerts"))
    bind.execute(sa.text("DELETE FROM clients"))
    bind.execute(sa.text("DELETE FROM sales_agents"))
    bind.execute(sa.text("DELETE FROM regional_managers"))
    bind.execute(sa.text("DELETE FROM regions"))

    # ── 4. Re-seed regions, managers, agents ─────────────────────
    regions_t  = sa.table("regions",          sa.column("id"), sa.column("slug"), sa.column("name"), sa.column("display_order"))
    managers_t = sa.table("regional_managers",sa.column("id"), sa.column("region_id"), sa.column("name"), sa.column("email"))
    agents_t   = sa.table("sales_agents",     sa.column("id"), sa.column("manager_id"), sa.column("name"), sa.column("email"))

    op.bulk_insert(regions_t,  REGIONS)
    op.bulk_insert(managers_t, MANAGERS)
    op.bulk_insert(agents_t,   AGENTS)

    # ── 5. Load CSV ───────────────────────────────────────────────
    csv_path = CSV_PATH if os.path.exists(CSV_PATH) else CSV_PATH_LOCAL
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"alerts.csv not found at {CSV_PATH} or {CSV_PATH_LOCAL}. "
            "Ensure ./IA is mounted as /app/ia_data in docker-compose."
        )

    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    # ── 6. Build unique client list ───────────────────────────────
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

    seen_csv_client_ids: dict[str, int] = {}  # csv client_id → db id
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

    # ── 7. Load alerts ────────────────────────────────────────────
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

        # due_at from predicted_next_purchase or fallback
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
    # Remove added columns; data loss is acceptable (was reseeded)
    op.drop_column("regional_alerts", "alert_context_json")
    op.drop_column("regional_alerts", "last_order_date")
    op.drop_column("regional_alerts", "predicted_next_purchase")
    op.drop_column("regional_alerts", "dismiss_reason")
    op.drop_column("regional_alerts", "churn_type")
    op.drop_column("regional_alerts", "explanation")
    op.drop_column("clients", "zone")
    op.drop_column("clients", "comunidad_autonoma")
    op.drop_column("clients", "provincia")
