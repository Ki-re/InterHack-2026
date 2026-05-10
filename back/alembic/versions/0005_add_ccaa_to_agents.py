"""add cod_ccaa to sales_agents

Revision ID: 0005_add_ccaa_to_agents
Revises: 0004_create_notifications
Create Date: 2026-05-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_add_ccaa_to_agents"
down_revision = "0004_create_notifications"
branch_labels = None
depends_on = None

# Agent id → cod_ccaa assignment
# Est:   1=Catalunya(09), 2=C.Valenciana(10), 3=Murcia(14)
# North: 4=PaísBasc(16),  5=Navarra(15),      6=LaRioja(17)
# South: 7=Andalucía(01), 8=Madrid(13),        9=Extremadura(11)
_AGENT_CCAA = {
    1: "09",
    2: "10",
    3: "14",
    4: "16",
    5: "15",
    6: "17",
    7: "01",
    8: "13",
    9: "11",
}


def upgrade() -> None:
    op.add_column(
        "sales_agents",
        sa.Column("cod_ccaa", sa.String(2), nullable=False, server_default=""),
    )
    conn = op.get_bind()
    for agent_id, cod in _AGENT_CCAA.items():
        conn.execute(
            sa.text("UPDATE sales_agents SET cod_ccaa = :cod WHERE id = :id"),
            {"cod": cod, "id": agent_id},
        )


def downgrade() -> None:
    op.drop_column("sales_agents", "cod_ccaa")
