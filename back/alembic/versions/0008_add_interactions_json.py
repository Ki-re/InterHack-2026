"""add interactions_json and events_json to regional_alerts

Revision ID: 0008_add_interactions_json
Revises: 0007_merge_heads
Create Date: 2026-05-10 00:00:00.000000

Adds two nullable TEXT columns to store JSON arrays of interaction records and
system events directly on each alert row, so the demo seed script can inject
realistic activity history and the API can serve it to the frontend.
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_add_interactions_json"
down_revision = "0007_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("regional_alerts") as batch_op:
        batch_op.add_column(sa.Column("interactions_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("events_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("regional_alerts") as batch_op:
        batch_op.drop_column("events_json")
        batch_op.drop_column("interactions_json")
