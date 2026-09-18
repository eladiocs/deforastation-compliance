from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry


class PointField(BaseModel):
    geometry: dict = Field(..., description="GeoJSON Point with the property location")

    @field_validator("geometry")
    @classmethod
    def validate_geometry(cls, v: dict) -> dict:
        try:
            geom: BaseGeometry = shape(v)
        except Exception as exc:
            raise ValueError(f"Invalid GeoJSON geometry: {exc}") from exc
        if geom.geom_type != "Point":
            raise ValueError(f"geometry must be a Point, got {geom.geom_type}")
        return v


class ParcelCreateRequest(PointField):
    name: str
    address: str | None = None


class ParcelUpdateRequest(BaseModel):
    name: str
    address: str | None = None


class ParcelOut(BaseModel):
    id: int
    name: str
    address: str | None
    geometry: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisCreateRequest(BaseModel):
    buffer_radius_m: float = Field(
        default=300.0,
        ge=50.0,
        le=2000.0,
        description="Radio de análisis alrededor del punto, en metros",
    )


class RiskFactor(BaseModel):
    key: str
    label: str
    value: float
    unit: str
    severity: Literal["bajo", "medio", "alto"]


class AnalysisOut(BaseModel):
    id: int
    parcel_id: int
    buffer_radius_m: float
    elevation_m: float
    relative_elevation_m: float
    slope_pct: float
    water_occurrence_pct: float
    distance_to_water_m: float
    distance_to_channel_m: float
    risk_score: float
    risk_label: Literal["bajo", "medio", "alto", "muy_alto"]
    risk_factors: list[RiskFactor]
    dataset_notes: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
