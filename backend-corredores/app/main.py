from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import graph_service
from .config import settings
from .models import (
    BuildGraphRequest,
    GenerateStudyAreaRequest,
    GraphResponse,
    ImpactAnalysisRequest,
    ImpactAnalysisResult,
    Patch,
    ShortestPathRequest,
    ShortestPathResult,
)
from .routers import analyses as analyses_router
from .routers import parcels as parcels_router

# Tables are created/versioned via Alembic (`alembic upgrade head`), not create_all.

app = FastAPI(title="BioConnect API", version="0.1.0")

allowed_origins = settings.CORS_ORIGINS.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parcels_router.router)
app.include_router(analyses_router.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


OSM_FETCH_ERROR_DETAIL = (
    "No se pudieron obtener los datos de hábitat de OpenStreetMap. "
    "Puede que Overpass no esté disponible en este momento."
)


@app.post("/study-area/generate", response_model=list[Patch])
def generate_study_area(request: GenerateStudyAreaRequest) -> list[Patch]:
    try:
        patches, _source_groups = graph_service.generate_study_area(request.polygon, request.count)
        return patches
    except Exception as exc:
        raise HTTPException(status_code=502, detail=OSM_FETCH_ERROR_DETAIL) from exc


@app.post("/graph/build", response_model=GraphResponse)
def build_graph(request: BuildGraphRequest) -> GraphResponse:
    edges = graph_service.build_corridors(request.patches, request.dispersal_distance)
    annotated_edges, metrics = graph_service.analyze_graph(request.patches, edges)
    return GraphResponse(edges=annotated_edges, metrics=metrics)


@app.post("/graph/shortest-path", response_model=ShortestPathResult)
def shortest_path(request: ShortestPathRequest) -> ShortestPathResult:
    edges = graph_service.build_corridors(request.patches, request.dispersal_distance)
    result = graph_service.shortest_path(
        request.patches, edges, request.source_id, request.target_id
    )
    if result is None:
        raise HTTPException(status_code=404, detail="No hay corredor entre los parches seleccionados")
    return result


@app.post("/impact-analysis", response_model=ImpactAnalysisResult)
def impact_analysis(request: ImpactAnalysisRequest) -> ImpactAnalysisResult:
    try:
        return graph_service.analyze_impact(
            request.footprint,
            request.dispersal_distance,
            request.count,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=OSM_FETCH_ERROR_DETAIL) from exc
