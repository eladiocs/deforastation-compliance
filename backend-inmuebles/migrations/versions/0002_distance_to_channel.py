"""add analyses.distance_to_channel_m (MERIT Hydro drainage-channel proximity)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-18
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("distance_to_channel_m", sa.Float, nullable=False, server_default="1000"),
        schema="inmuebles",
    )
    op.alter_column("analyses", "distance_to_channel_m", server_default=None, schema="inmuebles")


def downgrade() -> None:
    op.drop_column("analyses", "distance_to_channel_m", schema="inmuebles")
