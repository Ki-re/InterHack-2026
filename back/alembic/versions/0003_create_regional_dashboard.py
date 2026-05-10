"""create regional dashboard tables

Revision ID: 0003_create_regional_dashboard
Revises: 0002_create_users
Create Date: 2026-05-09 00:00:00.000000
"""

from datetime import datetime, timedelta

from alembic import op
import sqlalchemy as sa


revision = "0003_create_regional_dashboard"
down_revision = "0002_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "regional_managers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_regional_managers_region_id", "regional_managers", ["region_id"])
    op.create_table(
        "sales_agents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("manager_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["manager_id"], ["regional_managers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_sales_agents_manager_id", "sales_agents", ["manager_id"])
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("customer_value", sa.String(length=20), nullable=False),
        sa.Column("segment", sa.String(length=80), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["sales_agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clients_agent_id", "clients", ["agent_id"])
    op.create_table(
        "regional_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("churn_probability", sa.Integer(), nullable=False),
        sa.Column("purchase_propensity", sa.Integer(), nullable=False),
        sa.Column("estimated_value", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regional_alerts_client_id", "regional_alerts", ["client_id"])

    _seed_dashboard_data()


def downgrade() -> None:
    op.drop_index("ix_regional_alerts_client_id", table_name="regional_alerts")
    op.drop_table("regional_alerts")
    op.drop_index("ix_clients_agent_id", table_name="clients")
    op.drop_table("clients")
    op.drop_index("ix_sales_agents_manager_id", table_name="sales_agents")
    op.drop_table("sales_agents")
    op.drop_index("ix_regional_managers_region_id", table_name="regional_managers")
    op.drop_table("regional_managers")
    op.drop_table("regions")


def _seed_dashboard_data() -> None:
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
    )
    clients = sa.table(
        "clients",
        sa.column("id", sa.Integer),
        sa.column("agent_id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("customer_value", sa.String),
        sa.column("segment", sa.String),
    )
    alerts = sa.table(
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

    op.bulk_insert(
        regions,
        [
            {"id": 1, "slug": "est", "name": "Est", "display_order": 1},
            {"id": 2, "slug": "north", "name": "North", "display_order": 2},
            {"id": 3, "slug": "south", "name": "South", "display_order": 3},
        ],
    )

    manager_rows = [
        {"id": 1, "region_id": 1, "name": "Marta Soler",    "email": "marta.soler@inibsa.local"},
        {"id": 2, "region_id": 2, "name": "Ane Etxebarria", "email": "ane.etxebarria@inibsa.local"},
        {"id": 3, "region_id": 3, "name": "Lucia Navarro",  "email": "lucia.navarro@inibsa.local"},
    ]
    op.bulk_insert(managers, manager_rows)

    # 3 agents per manager (ids 1–9)
    agent_names = [
        # region 1 — Est (manager 1)
        ("Clara Puig",    "clara.puig",    1),
        ("Marc Vidal",    "marc.vidal",    1),
        ("Nuria Costa",   "nuria.costa",   1),
        # region 2 — North (manager 2)
        ("Iker Alonso",   "iker.alonso",   2),
        ("Leire Martin",  "leire.martin",  2),
        ("Jordi Roca",    "jordi.roca",    2),
        # region 3 — South (manager 3)
        ("Sofia Prieto",  "sofia.prieto",  3),
        ("Hugo Campos",   "hugo.campos",   3),
        ("Carmen Vega",   "carmen.vega",   3),
    ]
    agent_rows = [
        {
            "id": idx + 1,
            "manager_id": mgr_id,
            "name": name,
            "email": f"{email}@inibsa.local",
        }
        for idx, (name, email, mgr_id) in enumerate(agent_names)
    ]
    op.bulk_insert(agents, agent_rows)

    # 3 clients per agent — real dental/pharma clinic names (27 total)
    client_names = [
        # agent 1 — Clara Puig
        "Clínica Dental Armonía",       "Dentix Barcelona Centre",      "Ortodoncia Gaudí",
        # agent 2 — Marc Vidal
        "Clínica Dental Mediterrànea",  "Centre Dental Eixample",       "Implantodonts Sarrià",
        # agent 3 — Nuria Costa
        "Dental Clínic Rambla",         "Odontopress Valencia",         "Clínica Dental Blasco",
        # agent 4 — Iker Alonso
        "Bilbao Dental Center",         "Clínica Etxe Osasun",         "Ortodontzia Bizkaia",
        # agent 5 — Leire Martin
        "Clínica Dental Donostia",      "Periodoncia San Sebastián",    "Implantes Gipuzkoa",
        # agent 6 — Jordi Roca
        "Dental Navarra Salud",         "Clínica Pamplona Dental",     "Ortodontics La Rioja",
        # agent 7 — Sofia Prieto
        "Clínica Dental Sevilla Sur",   "Odontología Triana",          "Centro Dental Giralda",
        # agent 8 — Hugo Campos
        "Dental Málaga Costa",          "Clínica Oral Marbella",       "Implantes Torremolinos",
        # agent 9 — Carmen Vega
        "Clínica Dental Granada",       "Odontología Alhambra",        "Centro Dental Córdoba",
    ]
    segment_cycle = ["Clinica dental", "Distribuidor", "Hospital", "Laboratorio"]
    client_rows = []
    for agent_idx, agent in enumerate(agent_rows):
        for offset in range(3):
            client_id = agent_idx * 3 + offset + 1
            client_rows.append(
                {
                    "id": client_id,
                    "agent_id": agent["id"],
                    "name": client_names[client_id - 1],
                    "customer_value": ["high", "medium", "low"][client_id % 3],
                    "segment": segment_cycle[client_id % len(segment_cycle)],
                }
            )
    op.bulk_insert(clients, client_rows)

    base_date = datetime(2026, 5, 1, 9, 0, 0)
    statuses = ["attended", "pending", "attended", "dismissed", "pending", "attended"]
    risks = ["high", "medium", "low", "high", "medium", "high"]
    alert_rows = []
    alert_id = 1
    for client in client_rows:
        for offset in range(2):
            status = statuses[(client["id"] + offset) % len(statuses)]
            created_at = base_date + timedelta(hours=alert_id * 5)
            due_at = created_at + timedelta(hours=36 + (offset * 12))
            alert_rows.append(
                {
                    "id": alert_id,
                    "client_id": client["id"],
                    "status": status,
                    "risk_level": risks[(client["id"] + offset) % len(risks)],
                    "churn_probability": min(94, 28 + ((client["id"] * 7 + offset * 11) % 67)),
                    "purchase_propensity": min(96, 22 + ((client["id"] * 9 + offset * 13) % 72)),
                    "estimated_value": float(1200 + (client["id"] * 315) + (offset * 475)),
                    "created_at": created_at,
                    "due_at": due_at,
                    "attended_at": created_at + timedelta(hours=10 + (client["id"] % 18))
                    if status == "attended"
                    else None,
                    "dismissed_at": created_at + timedelta(hours=8) if status == "dismissed" else None,
                }
            )
            alert_id += 1
    op.bulk_insert(alerts, alert_rows)
