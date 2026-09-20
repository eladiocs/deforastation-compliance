from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Parcel(Base):
    __tablename__ = "parcels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    analyses: Mapped[list["Analysis"]] = relationship(back_populates="parcel", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False)

    elevation_m: Mapped[float] = mapped_column(Float, nullable=False)
    hand_m: Mapped[float] = mapped_column(Float, nullable=False)
    slope_pct: Mapped[float] = mapped_column(Float, nullable=False)
    water_occurrence_pct: Mapped[float] = mapped_column(Float, nullable=False)
    distance_to_water_m: Mapped[float] = mapped_column(Float, nullable=False)
    distance_to_channel_m: Mapped[float] = mapped_column(Float, nullable=False)

    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_label: Mapped[str] = mapped_column(String, nullable=False)
    risk_factors: Mapped[list] = mapped_column(JSON, nullable=False)
    dataset_notes: Mapped[list] = mapped_column(JSON, nullable=False)

    report_pdf_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    parcel: Mapped["Parcel"] = relationship(back_populates="analyses")
