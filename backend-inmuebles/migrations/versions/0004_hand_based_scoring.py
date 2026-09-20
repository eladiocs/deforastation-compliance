"""replace buffer-relative elevation with point-based HAND, drop buffer_radius_m

The whole analysis is per-point (a single building/dwelling), so there is no
sensible neighborhood to average over: `buffer_radius_m` only fed
`relative_elevation_m`, a simplified "height above the lowest point in an
arbitrary buffer" proxy for what MERIT Hydro's own HAND (Height Above
Nearest Drainage) band already gives directly, evaluated at the point.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-20
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("hand_m", sa.Float, nullable=False, server_default="0"),
        schema="inmuebles",
    )
    op.alter_column("analyses", "hand_m", server_default=None, schema="inmuebles")
    op.drop_column("analyses", "relative_elevation_m", schema="inmuebles")
    op.drop_column("analyses", "buffer_radius_m", schema="inmuebles")


def downgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("buffer_radius_m", sa.Float, nullable=False, server_default="300"),
        schema="inmuebles",
    )
    op.alter_column("analyses", "buffer_radius_m", server_default=None, schema="inmuebles")
    op.add_column(
        "analyses",
        sa.Column("relative_elevation_m", sa.Float, nullable=False, server_default="0"),
        schema="inmuebles",
    )
    op.alter_column("analyses", "relative_elevation_m", server_default=None, schema="inmuebles")
    op.drop_column("analyses", "hand_m", schema="inmuebles")
