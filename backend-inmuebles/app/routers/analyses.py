from fastapi import APIRouter, Depends, HTTPException, Response
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.flood_analysis import analyze_point
from app.report_generator import generate_report_pdf
from app.schemas import AnalysisOut

router = APIRouter(tags=["analyses"])


def _get_parcel_or_404(parcel_id: int, db: Session) -> models.Parcel:
    parcel = db.get(models.Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")
    return parcel


def _get_analysis_or_404(analysis_id: int, db: Session) -> models.Analysis:
    analysis = db.get(models.Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    return analysis


@router.post("/parcels/{parcel_id}/analyses", response_model=AnalysisOut)
def create_analysis(parcel_id: int, db: Session = Depends(get_db)) -> models.Analysis:
    parcel = _get_parcel_or_404(parcel_id, db)
    point = to_shape(parcel.geom)

    try:
        result = analyze_point(lat=point.y, lng=point.x)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Earth Engine analysis failed: {exc}") from exc

    analysis = models.Analysis(parcel_id=parcel.id, **result)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    analysis.report_pdf_data = generate_report_pdf(analysis, parcel.name, parcel.address)
    db.commit()
    db.refresh(analysis)

    return analysis


@router.get("/parcels/{parcel_id}/analyses", response_model=list[AnalysisOut])
def list_analyses(parcel_id: int, db: Session = Depends(get_db)) -> list[models.Analysis]:
    _get_parcel_or_404(parcel_id, db)
    return (
        db.query(models.Analysis)
        .filter(models.Analysis.parcel_id == parcel_id)
        .order_by(models.Analysis.created_at.desc())
        .all()
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)) -> models.Analysis:
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
    pdf_bytes = analysis.report_pdf_data or generate_report_pdf(analysis, parcel.name, parcel.address)
    slug = "".join(c if c.isalnum() else "-" for c in parcel.name.lower()).strip("-") or "informe"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="informe-riesgo-inundacion-{slug}.pdf"'},
    )
