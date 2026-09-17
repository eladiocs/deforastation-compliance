"""initial schema: corredores.parcels and corredores.analyses

Revision ID: 0001
Revises:
Create Date: 2026-09-17
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
    op.execute("CREATE SCHEMA IF NOT EXISTS corredores")

    op.create_table(
        "parcels",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.Geometry("GEOMETRY", srid=4326),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime, nullable=False),
        schema="corredores",
    )

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "parcel_id",
            sa.Integer,
            sa.ForeignKey("corredores.parcels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dispersal_distance", sa.Float, nullable=False),
        sa.Column("dispersal_label", sa.String, nullable=False),
        sa.Column("count", sa.Integer, nullable=False),
        sa.Column("project_meta", sa.JSON, nullable=False),
        sa.Column("result", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        schema="corredores",
    )
    op.create_index("ix_corredores_analyses_parcel_id", "analyses", ["parcel_id"], schema="corredores")


def downgrade() -> None:
    op.drop_index("ix_corredores_analyses_parcel_id", table_name="analyses", schema="corredores")
    op.drop_table("analyses", schema="corredores")
    op.drop_table("parcels", schema="corredores")
