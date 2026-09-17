"""store report PDF bytes in the database instead of local disk

The PDF used to be written to a path on the container's local filesystem
(report_pdf_path). On Render's free tier the filesystem is not guaranteed to
survive a sleep/wake cycle, so the file could disappear while the DB row
referencing it remained — producing a 500 on download. The PDF bytes are now
stored directly in the row.

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
    op.add_column("analyses", sa.Column("report_pdf_data", sa.LargeBinary, nullable=True))
    op.drop_column("analyses", "report_pdf_path")


def downgrade() -> None:
    op.add_column("analyses", sa.Column("report_pdf_path", sa.String, nullable=True))
    op.drop_column("analyses", "report_pdf_data")
