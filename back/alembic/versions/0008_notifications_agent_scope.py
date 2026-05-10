"""notifications: make user_id nullable, drop FK, add agent_id

Revision ID: 0008_notifications_agent_scope
Revises: 0007_merge_heads
Create Date: 2026-05-10 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_notifications_agent_scope"
down_revision = "0007_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("notifications", recreate="always") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.add_column(sa.Column("agent_id", sa.Integer(), nullable=True))

    op.create_index("ix_notifications_agent_id", "notifications", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_agent_id", table_name="notifications")
    with op.batch_alter_table("notifications", recreate="always") as batch_op:
        batch_op.drop_column("agent_id")
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
