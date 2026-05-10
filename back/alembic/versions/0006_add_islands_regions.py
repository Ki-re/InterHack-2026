"""add Baleares and Canarias regions with agents, clients and alerts

Revision ID: 0006_add_islands_regions
Revises: 0005_add_ccaa_to_agents
Create Date: 2026-05-10 00:00:00.000000
"""

from datetime import datetime, timedelta

from alembic import op
import sqlalchemy as sa


revision = "0006_add_islands_regions"
down_revision = "0005_add_ccaa_to_agents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    regions = sa.table(
        "regions",
        sa.column("id", sa.Integer),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("display_order", sa.Integer),
    )
    managers = sa.table(
        "regional_managers",
        sa.column("id", sa.Integer),
        sa.column("region_id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("email", sa.String),
    )
    agents = sa.table(
        "sales_agents",
        sa.column("id", sa.Integer),
        sa.column("manager_id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("email", sa.String),
        sa.column("cod_ccaa", sa.String),
    )
    clients = sa.table(
        "clients",
        sa.column("id", sa.Integer),
        sa.column("agent_id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("customer_value", sa.String),
        sa.column("segment", sa.String),
    )
    alerts_tbl = sa.table(
        "regional_alerts",
        sa.column("id", sa.Integer),
        sa.column("client_id", sa.Integer),
        sa.column("status", sa.String),
        sa.column("risk_level", sa.String),
        sa.column("churn_probability", sa.Integer),
        sa.column("purchase_propensity", sa.Integer),
        sa.column("estimated_value", sa.Float),
        sa.column("created_at", sa.DateTime),
        sa.column("due_at", sa.DateTime),
        sa.column("attended_at", sa.DateTime),
        sa.column("dismissed_at", sa.DateTime),
    )

    op.bulk_insert(regions, [
        {"id": 4, "slug": "baleares", "name": "Baleares", "display_order": 4},
        {"id": 5, "slug": "canarias", "name": "Canarias", "display_order": 5},
    ])

    op.bulk_insert(managers, [
        {"id": 4, "region_id": 4, "name": "Jaume Esteva",  "email": "jaume.esteva@inibsa.local"},
        {"id": 5, "region_id": 5, "name": "Carmen Reyes",  "email": "carmen.reyes@inibsa.local"},
    ])

    op.bulk_insert(agents, [
        # Baleares (manager 4) — cod_ccaa 04
        {"id": 10, "manager_id": 4, "name": "Pau Ramis",     "email": "pau.ramis@inibsa.local",    "cod_ccaa": "04"},
        {"id": 11, "manager_id": 4, "name": "Maria Bauçà",   "email": "maria.bauca@inibsa.local",  "cod_ccaa": "04"},
        {"id": 12, "manager_id": 4, "name": "Tomàs Fiol",    "email": "tomas.fiol@inibsa.local",   "cod_ccaa": "04"},
        # Canarias (manager 5) — cod_ccaa 05
        {"id": 13, "manager_id": 5, "name": "Elena Rivero",  "email": "elena.rivero@inibsa.local", "cod_ccaa": "05"},
        {"id": 14, "manager_id": 5, "name": "Diego Santos",  "email": "diego.santos@inibsa.local", "cod_ccaa": "05"},
        {"id": 15, "manager_id": 5, "name": "Isabel Correa", "email": "isabel.correa@inibsa.local","cod_ccaa": "05"},
    ])

    client_data = [
        # agent 10 — Pau Ramis (Baleares)
        (28, 10, "Clínica Dental Mallorca",       "high",   "Clinica dental"),
        (29, 10, "Ortodontics Palma",              "medium", "Distribuidor"),
        (30, 10, "Dental Calvià",                  "low",    "Hospital"),
        # agent 11 — Maria Bauçà (Baleares)
        (31, 11, "Clínica Eivissa Dental",         "high",   "Clinica dental"),
        (32, 11, "Dental Menorca",                 "medium", "Laboratorio"),
        (33, 11, "Implants Formentera",            "low",    "Clinica dental"),
        # agent 12 — Tomàs Fiol (Baleares)
        (34, 12, "Centre Dental Illes",            "high",   "Distribuidor"),
        (35, 12, "Periodoncia Balear",             "medium", "Clinica dental"),
        (36, 12, "Dental Ses Salines",             "low",    "Hospital"),
        # agent 13 — Elena Rivero (Canarias)
        (37, 13, "Clínica Dental Tenerife",        "high",   "Clinica dental"),
        (38, 13, "Ortodoncias Santa Cruz",         "medium", "Distribuidor"),
        (39, 13, "Implantes Canarias",             "low",    "Clinica dental"),
        # agent 14 — Diego Santos (Canarias)
        (40, 14, "Dental Las Palmas Centro",       "high",   "Hospital"),
        (41, 14, "Clínica Gran Canaria Sur",       "medium", "Clinica dental"),
        (42, 14, "Periodoncia Lanzarote",          "low",    "Laboratorio"),
        # agent 15 — Isabel Correa (Canarias)
        (43, 15, "Clínica Dental Fuerteventura",   "high",   "Clinica dental"),
        (44, 15, "Dental La Palma",                "medium", "Distribuidor"),
        (45, 15, "Centro Oral La Gomera",          "low",    "Hospital"),
    ]
    op.bulk_insert(clients, [
        {"id": cid, "agent_id": aid, "name": name, "customer_value": cv, "segment": seg}
        for cid, aid, name, cv, seg in client_data
    ])

    base_date = datetime(2026, 5, 1, 9, 0, 0)
    statuses = ["attended", "pending", "attended", "dismissed", "pending", "attended"]
    risks = ["high", "medium", "low", "high", "medium", "high"]
    alert_rows = []
    alert_id = 55
    for cid, _, _, _, _ in client_data:
        for offset in range(2):
            status = statuses[(cid + offset) % len(statuses)]
            created_at = base_date + timedelta(hours=alert_id * 5)
            due_at = created_at + timedelta(hours=36 + offset * 12)
            alert_rows.append({
                "id": alert_id,
                "client_id": cid,
                "status": status,
                "risk_level": risks[(cid + offset) % len(risks)],
                "churn_probability": min(94, 28 + ((cid * 7 + offset * 11) % 67)),
                "purchase_propensity": min(96, 22 + ((cid * 9 + offset * 13) % 72)),
                "estimated_value": float(1200 + cid * 315 + offset * 475),
                "created_at": created_at,
                "due_at": due_at,
                "attended_at": created_at + timedelta(hours=10 + cid % 18) if status == "attended" else None,
                "dismissed_at": created_at + timedelta(hours=8) if status == "dismissed" else None,
            })
            alert_id += 1
    op.bulk_insert(alerts_tbl, alert_rows)


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM regional_alerts WHERE id >= 55"))
    conn.execute(sa.text("DELETE FROM clients WHERE id >= 28"))
    conn.execute(sa.text("DELETE FROM sales_agents WHERE id >= 10"))
    conn.execute(sa.text("DELETE FROM regional_managers WHERE id >= 4"))
    conn.execute(sa.text("DELETE FROM regions WHERE id >= 4"))
