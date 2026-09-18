"""initial schema: inmuebles.parcels and inmuebles.analyses

Revision ID: 0001
Revises:
Create Date: 2026-09-18
"""
import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE SCHEMA IF NOT EXISTS inmuebles")

    op.create_table(
        "parcels",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("address", sa.String, nullable=True),
        sa.Column("client_name", sa.String, nullable=True),
        sa.Column("geom", geoalchemy2.Geometry("POINT", srid=4326), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        schema="inmuebles",
    )

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "parcel_id",
            sa.Integer,
            sa.ForeignKey("inmuebles.parcels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("buffer_radius_m", sa.Float, nullable=False),
        sa.Column("elevation_m", sa.Float, nullable=False),
        sa.Column("relative_elevation_m", sa.Float, nullable=False),
        sa.Column("slope_pct", sa.Float, nullable=False),
        sa.Column("water_occurrence_pct", sa.Float, nullable=False),
        sa.Column("distance_to_water_m", sa.Float, nullable=False),
        sa.Column("risk_score", sa.Float, nullable=False),
        sa.Column("risk_label", sa.String, nullable=False),
        sa.Column("risk_factors", sa.JSON, nullable=False),
        sa.Column("dataset_notes", sa.JSON, nullable=False),
        sa.Column("report_pdf_data", sa.LargeBinary, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        schema="inmuebles",
    )
    op.create_index("ix_inmuebles_analyses_parcel_id", "analyses", ["parcel_id"], schema="inmuebles")


def downgrade() -> None:
    op.drop_index("ix_inmuebles_analyses_parcel_id", table_name="analyses", schema="inmuebles")
    op.drop_table("analyses", schema="inmuebles")
    op.drop_table("parcels", schema="inmuebles")
