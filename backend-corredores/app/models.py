from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Patch(CamelModel):
    id: str
    name: str
    lat: float
    lng: float
    radius: float


class LatLngPoint(CamelModel):
    lat: float
    lng: float


class CorridorEdge(CamelModel):
    source: str
    target: str
    distance: float
    resistance: float
    cost: float
    betweenness: float = 0.0
    route: list[LatLngPoint] = []


class TopCorridor(CamelModel):
    edge: CorridorEdge
    betweenness: float


class GraphMetrics(CamelModel):
    total_patches: int
    total_corridors: int
    component_count: int
    isolated_patch_ids: list[str]
    largest_component_size: int
    fragmentation_index: float
    top_corridors: list[TopCorridor]


class ShortestPathResult(CamelModel):
    patch_ids: list[str]
    total_cost: float


class BuildGraphRequest(CamelModel):
    patches: list[Patch]
    dispersal_distance: float


class ShortestPathRequest(BuildGraphRequest):
    source_id: str
    target_id: str


class GraphResponse(CamelModel):
    edges: list[CorridorEdge]
    metrics: GraphMetrics


class GenerateStudyAreaRequest(CamelModel):
    polygon: list[LatLngPoint]
    count: int = 10

    @field_validator("polygon")
    @classmethod
    def _min_vertices(cls, value: list[LatLngPoint]) -> list[LatLngPoint]:
        if len(value) < 3:
            raise ValueError("polygon must have at least 3 vertices")
        return value


class ImpactAnalysisRequest(CamelModel):
    footprint: list[LatLngPoint]
    dispersal_distance: float
    count: int = 15

    @field_validator("footprint")
    @classmethod
    def _min_vertices(cls, value: list[LatLngPoint]) -> list[LatLngPoint]:
        if len(value) < 3:
            raise ValueError("footprint must have at least 3 vertices")
        return value


class ImpactAnalysisResult(CamelModel):
    footprint: list[LatLngPoint]
    dispersal_distance: float
    patches: list[Patch]
    patches_lost: list[Patch]
    baseline: GraphResponse
    scenario: GraphResponse
    corridors_lost: list[CorridorEdge]
    corridors_unaffected_count: int
    newly_isolated_patch_ids: list[str]
    fragmentation_delta: float


class ProjectMeta(CamelModel):
    description: str = ""
    prepared_by: str = ""


class AnalysisCreateRequest(CamelModel):
    dispersal_distance: float
    dispersal_label: str
    count: int = 15
    project_meta: ProjectMeta = ProjectMeta()


class AnalysisOut(CamelModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: int
    parcel_id: int
    dispersal_distance: float
    dispersal_label: str
    count: int
    project_meta: ProjectMeta
    result: ImpactAnalysisResult
    created_at: datetime


class ParcelCreateRequest(CamelModel):
    name: str
    footprint: list[LatLngPoint]

    @field_validator("name")
    @classmethod
    def _non_empty_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be empty")
        return value.strip()

    @field_validator("footprint")
    @classmethod
    def _min_vertices(cls, value: list[LatLngPoint]) -> list[LatLngPoint]:
        if len(value) < 3:
            raise ValueError("footprint must have at least 3 vertices")
        return value


class ParcelUpdateRequest(CamelModel):
    name: str

    @field_validator("name")
    @classmethod
    def _non_empty_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be empty")
        return value.strip()


class ParcelOut(CamelModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: int
    name: str
    footprint: list[LatLngPoint]
    created_at: datetime
