"""merge two parallel branches and fix cod_ccaa for all agents

Revision ID: 0007_merge_heads
Revises: 0006_reload_alerts_csv, 0006_add_islands_regions
Create Date: 2026-05-10 00:00:00.000000

Merges:
  - branch A: 0005_load_alerts_from_csv -> 0006_reload_alerts_csv
    (5-zone seeding + real CSV data)
  - branch B: 0005_add_ccaa_to_agents -> 0006_add_islands_regions
    (cod_ccaa column; island data handled as no-op)

After the merge we set correct cod_ccaa values for all 13 agents based on
the zone assignment used in 0005_load_alerts_from_csv:
  north  (1-3):  P.Vasco(16), Navarra(15), La Rioja(17)
  east   (4-6):  Catalunya(09), C.Valenciana(10), Murcia(14)
  south  (7-9):  Andalucía(01), Madrid(13), Extremadura(11)
  canary (10-12): Canarias(05)
  balearic (13):  Illes Balears(04)
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_merge_heads"
down_revision = ("0006_reload_alerts_csv", "0006_add_islands_regions")
branch_labels = None
depends_on = None

# Agent id -> Spanish CCAA code (INE standard 2-digit codes)
_AGENT_CCAA = {
    # north zone
    1:  "16",  # País Vasco
    2:  "15",  # Navarra
    3:  "17",  # La Rioja
    # east zone
    4:  "09",  # Catalunya
    5:  "10",  # Comunitat Valenciana
    6:  "14",  # Murcia
    # south zone
    7:  "01",  # Andalucía
    8:  "13",  # Madrid
    9:  "11",  # Extremadura
    # canary zone
    10: "05",  # Canarias
    11: "05",
    12: "05",
    # balearic zone
    13: "04",  # Illes Balears
}


def upgrade() -> None:
    conn = op.get_bind()
    for agent_id, cod in _AGENT_CCAA.items():
        conn.execute(
            sa.text("UPDATE sales_agents SET cod_ccaa = :cod WHERE id = :id"),
            {"cod": cod, "id": agent_id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE sales_agents SET cod_ccaa = ''"))
