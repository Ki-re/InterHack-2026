"""add Baleares and Canarias regions with agents, clients and alerts

Revision ID: 0006_add_islands_regions
Revises: 0005_add_ccaa_to_agents
Create Date: 2026-05-10 00:00:00.000000

NOTE: This migration is a no-op.  The island regions, managers, agents,
clients and alerts are fully handled by migration 0005_load_alerts_from_csv
(the other branch), which loads the complete dataset from alerts.csv.
Running both would cause UNIQUE constraint violations on regions.id=4,5 and
sales_agents.id=10-15.  The 0007_merge_heads migration reconciles both
branches and sets cod_ccaa correctly for all 13 agents.
"""

from alembic import op

revision = "0006_add_islands_regions"
down_revision = "0005_add_ccaa_to_agents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass  # superseded by 0005_load_alerts_from_csv + 0007_merge_heads


def downgrade() -> None:
    pass
