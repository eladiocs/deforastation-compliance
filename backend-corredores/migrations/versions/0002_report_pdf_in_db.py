"""store the impact report PDF bytes on the analysis row

Mirrors the same fix on the anti-deforestation backend: the PDF is now
generated once at analysis-creation time and persisted in the database
instead of being regenerated from scratch on every download.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-17
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
        sa.Column("report_pdf_data", sa.LargeBinary, nullable=True),
        schema="corredores",
    )


def downgrade() -> None:
    op.drop_column("analyses", "report_pdf_data", schema="corredores")
