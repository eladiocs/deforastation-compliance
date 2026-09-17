from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Parcel(Base):
    __tablename__ = "parcels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    geom: Mapped[str] = mapped_column(Geometry("GEOMETRY", srid=4326), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parcel_id: Mapped[int] = mapped_column(ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False)
    dispersal_distance: Mapped[float] = mapped_column(Float, nullable=False)
    dispersal_label: Mapped[str] = mapped_column(String, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    project_meta: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
