import uuid
from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Parcel(Base):
    __tablename__ = "parcels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    client_name: Mapped[str | None] = mapped_column(String, nullable=True)
    commodity: Mapped[str | None] = mapped_column(String, nullable=True)
    geom: Mapped[str] = mapped_column(Geometry("GEOMETRY", srid=4326), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    analyses: Mapped[list["Analysis"]] = relationship(back_populates="parcel", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parcel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parcels.id"), nullable=False)

    cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    min_tree_cover_pct: Mapped[int] = mapped_column(Integer, nullable=False)

    parcel_area_ha: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_forest_area_ha: Mapped[float] = mapped_column(Float, nullable=False)
    loss_after_cutoff_area_ha: Mapped[float] = mapped_column(Float, nullable=False)
    deforestation_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    compliance_status: Mapped[str] = mapped_column(String, nullable=False)

    yearly_loss_since_2001: Mapped[list] = mapped_column(JSON, nullable=False)
    ndvi_quarterly_series: Mapped[list] = mapped_column(JSON, nullable=False)
    dataset_notes: Mapped[list] = mapped_column(JSON, nullable=False)

    report_pdf_path: Mapped[str | None] = mapped_column(String, nullable=True)
    report_sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    report_signature_b64: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    parcel: Mapped["Parcel"] = relationship(back_populates="analyses")
