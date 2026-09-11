import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry


class GeometryField(BaseModel):
    geometry: dict = Field(
        ..., description="GeoJSON Polygon or MultiPolygon geometry of the parcel boundary"
    )

    @field_validator("geometry")
    @classmethod
    def validate_geometry(cls, v: dict) -> dict:
        try:
            geom: BaseGeometry = shape(v)
        except Exception as exc:
            raise ValueError(f"Invalid GeoJSON geometry: {exc}") from exc
        if geom.geom_type not in ("Polygon", "MultiPolygon"):
            raise ValueError(f"geometry must be a Polygon or MultiPolygon, got {geom.geom_type}")
        if not geom.is_valid:
            raise ValueError("geometry is not a valid (non-self-intersecting) polygon")
        return v


class ParcelCreateRequest(GeometryField):
    name: str
    client_name: str | None = None
    commodity: str


class ParcelUpdateRequest(BaseModel):
    name: str
    client_name: str | None = None
    commodity: str


class ParcelOut(BaseModel):
    id: uuid.UUID
    name: str
    client_name: str | None
    commodity: str | None
    geometry: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisCreateRequest(BaseModel):
    cutoff_date: date = Field(
        default=date(2020, 12, 31),
        description="EUDR deforestation cutoff date (default: 2020-12-31)",
    )
    min_tree_cover_pct: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Minimum year-2000 canopy cover percent to count a pixel as baseline forest",
    )


class YearlyLoss(BaseModel):
    year: int
    area_ha: float


class NdviPoint(BaseModel):
    period_start: date
    ndvi_mean: float | None


class AnalysisOut(BaseModel):
    id: uuid.UUID
    parcel_id: uuid.UUID
    cutoff_date: date
    min_tree_cover_pct: int
    parcel_area_ha: float
    baseline_forest_area_ha: float
    loss_after_cutoff_area_ha: float
    deforestation_detected: bool
    compliance_status: Literal["compliant", "non_compliant", "needs_review"]
    yearly_loss_since_2001: list[YearlyLoss]
    ndvi_quarterly_series: list[NdviPoint]
    dataset_notes: list[str]
    report_sha256: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
