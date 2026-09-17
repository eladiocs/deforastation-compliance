from fastapi import APIRouter, Depends, HTTPException, Response
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session

from .. import db_models, graph_service
from ..database import get_db
from ..models import AnalysisCreateRequest, AnalysisOut, LatLngPoint
from ..report_generator import generate_report_pdf

router = APIRouter(tags=["analyses"])

OSM_FETCH_ERROR_DETAIL = (
    "No se pudieron obtener los datos de hábitat de OpenStreetMap. "
    "Puede que Overpass no esté disponible en este momento."
)


def _get_parcel_or_404(parcel_id: int, db: Session) -> db_models.Parcel:
    parcel = db.get(db_models.Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")
    return parcel


def _get_analysis_or_404(analysis_id: int, db: Session) -> db_models.Analysis:
    analysis = db.get(db_models.Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    return analysis


def _parcel_footprint(parcel: db_models.Parcel) -> list[LatLngPoint]:
    ring = list(to_shape(parcel.geom).exterior.coords)[:-1]
    return [LatLngPoint(lat=lat, lng=lng) for lng, lat in ring]


@router.post("/parcels/{parcel_id}/analyses", response_model=AnalysisOut)
def create_analysis(
    parcel_id: int, request: AnalysisCreateRequest, db: Session = Depends(get_db)
) -> db_models.Analysis:
    parcel = _get_parcel_or_404(parcel_id, db)
    try:
        result = graph_service.analyze_impact(
            _parcel_footprint(parcel),
            request.dispersal_distance,
            request.count,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=OSM_FETCH_ERROR_DETAIL) from exc

    analysis = db_models.Analysis(
        parcel_id=parcel.id,
        dispersal_distance=request.dispersal_distance,
        dispersal_label=request.dispersal_label,
        count=request.count,
        project_meta=request.project_meta.model_dump(by_alias=True),
        result=result.model_dump(by_alias=True),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.get("/parcels/{parcel_id}/analyses", response_model=list[AnalysisOut])
def list_analyses(parcel_id: int, db: Session = Depends(get_db)) -> list[db_models.Analysis]:
    _get_parcel_or_404(parcel_id, db)
    return (
        db.query(db_models.Analysis)
        .filter(db_models.Analysis.parcel_id == parcel_id)
        .order_by(db_models.Analysis.created_at.desc())
        .all()
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)) -> db_models.Analysis:
    return _get_analysis_or_404(analysis_id, db)


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: int, db: Session = Depends(get_db)) -> None:
    analysis = _get_analysis_or_404(analysis_id, db)
    db.delete(analysis)
    db.commit()


@router.get("/analyses/{analysis_id}/report")
def download_analysis_report(analysis_id: int, db: Session = Depends(get_db)) -> Response:
    analysis = _get_analysis_or_404(analysis_id, db)
    parcel = _get_parcel_or_404(analysis.parcel_id, db)
    pdf_bytes = generate_report_pdf(analysis, parcel.name)
    slug = "".join(c if c.isalnum() else "-" for c in parcel.name.lower()).strip("-") or "informe"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="informe-impacto-{slug}.pdf"'},
    )
