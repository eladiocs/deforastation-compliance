import uuid

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import mapping, shape
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.forest_analysis import analyze_parcel
from app.report_generator import generate_report
from app.schemas import (
    AnalysisCreateRequest,
    AnalysisOut,
    ParcelCreateRequest,
    ParcelOut,
    ParcelUpdateRequest,
)
from app.storage import delete_report_pdf, save_report_pdf

router = APIRouter(prefix="/api/v1/parcels", tags=["parcels"])


def _parcel_out(parcel: models.Parcel) -> ParcelOut:
    return ParcelOut(
        id=parcel.id,
        name=parcel.name,
        client_name=parcel.client_name,
        commodity=parcel.commodity,
        geometry=mapping(to_shape(parcel.geom)),
        created_at=parcel.created_at,
    )


@router.post("", response_model=ParcelOut)
def create_parcel(request: ParcelCreateRequest, db: Session = Depends(get_db)) -> ParcelOut:
    geom = shape(request.geometry)
    parcel = models.Parcel(
        name=request.name,
        client_name=request.client_name,
        commodity=request.commodity,
        geom=from_shape(geom, srid=4326),
    )
    db.add(parcel)
    db.commit()
    db.refresh(parcel)
    return _parcel_out(parcel)


@router.get("", response_model=list[ParcelOut])
def list_parcels(db: Session = Depends(get_db)) -> list[ParcelOut]:
    parcels = db.query(models.Parcel).order_by(models.Parcel.created_at.desc()).all()
    return [_parcel_out(p) for p in parcels]


@router.get("/{parcel_id}", response_model=ParcelOut)
def get_parcel(parcel_id: uuid.UUID, db: Session = Depends(get_db)) -> ParcelOut:
    parcel = db.get(models.Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return _parcel_out(parcel)


@router.patch("/{parcel_id}", response_model=ParcelOut)
def update_parcel(
    parcel_id: uuid.UUID, request: ParcelUpdateRequest, db: Session = Depends(get_db)
) -> ParcelOut:
    parcel = db.get(models.Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found")

    parcel.name = request.name
    parcel.client_name = request.client_name
    parcel.commodity = request.commodity
    db.commit()
    db.refresh(parcel)
    return _parcel_out(parcel)


@router.delete("/{parcel_id}", status_code=204)
def delete_parcel(parcel_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    parcel = db.get(models.Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found")

    for analysis in parcel.analyses:
        delete_report_pdf(analysis.report_pdf_path)

    db.delete(parcel)
    db.commit()


@router.get("/{parcel_id}/analyses", response_model=list[AnalysisOut])
def list_parcel_analyses(parcel_id: uuid.UUID, db: Session = Depends(get_db)) -> list[AnalysisOut]:
    parcel = db.get(models.Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    analyses = (
        db.query(models.Analysis)
        .filter(models.Analysis.parcel_id == parcel_id)
        .order_by(models.Analysis.created_at.desc())
        .all()
    )
    return [AnalysisOut.model_validate(a) for a in analyses]


@router.post("/{parcel_id}/analyses", response_model=AnalysisOut)
def create_analysis(
    parcel_id: uuid.UUID, request: AnalysisCreateRequest, db: Session = Depends(get_db)
) -> AnalysisOut:
    parcel = db.get(models.Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found")

    geojson = mapping(to_shape(parcel.geom))
    try:
        result = analyze_parcel(
            geojson=geojson,
            cutoff_date=request.cutoff_date,
            min_tree_cover_pct=request.min_tree_cover_pct,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Earth Engine analysis failed: {exc}") from exc

    analysis = models.Analysis(
        parcel_id=parcel_id,
        cutoff_date=request.cutoff_date,
        min_tree_cover_pct=request.min_tree_cover_pct,
        **result,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    pdf_bytes, sha256_hex, signature_b64 = generate_report(parcel, analysis)
    analysis.report_pdf_path = save_report_pdf(analysis.id, pdf_bytes)
    analysis.report_sha256 = sha256_hex
    analysis.report_signature_b64 = signature_b64
    db.commit()
    db.refresh(analysis)

    return AnalysisOut.model_validate(analysis)
