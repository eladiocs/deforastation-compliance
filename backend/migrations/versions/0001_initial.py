"""initial schema: parcels and analyses

Revision ID: 0001
Revises:
Create Date: 2026-09-10
"""
import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "parcels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("client_name", sa.String, nullable=True),
        sa.Column("commodity", sa.String, nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.Geometry("GEOMETRY", srid=4326),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "parcel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("parcels.id"),
            nullable=False,
        ),
        sa.Column("cutoff_date", sa.Date, nullable=False),
        sa.Column("min_tree_cover_pct", sa.Integer, nullable=False),
        sa.Column("parcel_area_ha", sa.Float, nullable=False),
        sa.Column("baseline_forest_area_ha", sa.Float, nullable=False),
        sa.Column("loss_after_cutoff_area_ha", sa.Float, nullable=False),
        sa.Column("deforestation_detected", sa.Boolean, nullable=False),
        sa.Column("compliance_status", sa.String, nullable=False),
        sa.Column("yearly_loss_since_2001", sa.JSON, nullable=False),
        sa.Column("ndvi_quarterly_series", sa.JSON, nullable=False),
        sa.Column("dataset_notes", sa.JSON, nullable=False),
        sa.Column("report_pdf_path", sa.String, nullable=True),
        sa.Column("report_sha256", sa.String, nullable=True),
        sa.Column("report_signature_b64", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_analyses_parcel_id", "analyses", ["parcel_id"])


def downgrade() -> None:
    op.drop_index("ix_analyses_parcel_id", table_name="analyses")
    op.drop_table("analyses")
    op.drop_table("parcels")
