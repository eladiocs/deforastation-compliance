"""drop parcels.client_name (unused for this module)

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-18
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("parcels", "client_name", schema="inmuebles")


def downgrade() -> None:
    op.add_column("parcels", sa.Column("client_name", sa.String, nullable=True), schema="inmuebles")
