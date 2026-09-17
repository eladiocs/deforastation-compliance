from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from .. import db_models
from ..database import get_db
from ..models import LatLngPoint, ParcelCreateRequest, ParcelOut, ParcelUpdateRequest

router = APIRouter(prefix="/parcels", tags=["parcels"])


def _footprint_to_polygon(footprint: list[LatLngPoint]) -> Polygon:
    return Polygon([(p.lng, p.lat) for p in footprint])


def _parcel_to_out(parcel: db_models.Parcel) -> ParcelOut:
    ring = list(to_shape(parcel.geom).exterior.coords)[:-1]
    footprint = [LatLngPoint(lat=lat, lng=lng) for lng, lat in ring]
    return ParcelOut(id=parcel.id, name=parcel.name, footprint=footprint, created_at=parcel.created_at)


@router.post("", response_model=ParcelOut)
def create_parcel(request: ParcelCreateRequest, db: Session = Depends(get_db)) -> ParcelOut:
    parcel = db_models.Parcel(
        name=request.name,
        geom=from_shape(_footprint_to_polygon(request.footprint), srid=4326),
    )
    db.add(parcel)
    db.commit()
    db.refresh(parcel)
    return _parcel_to_out(parcel)


@router.get("", response_model=list[ParcelOut])
def list_parcels(db: Session = Depends(get_db)) -> list[ParcelOut]:
    parcels = db.query(db_models.Parcel).order_by(db_models.Parcel.created_at.desc()).all()
    return [_parcel_to_out(p) for p in parcels]


@router.get("/{parcel_id}", response_model=ParcelOut)
def get_parcel(parcel_id: int, db: Session = Depends(get_db)) -> ParcelOut:
    parcel = db.get(db_models.Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")
    return _parcel_to_out(parcel)


@router.patch("/{parcel_id}", response_model=ParcelOut)
def update_parcel(
    parcel_id: int, request: ParcelUpdateRequest, db: Session = Depends(get_db)
) -> ParcelOut:
    parcel = db.get(db_models.Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")
    parcel.name = request.name
    db.commit()
    db.refresh(parcel)
    return _parcel_to_out(parcel)


@router.delete("/{parcel_id}", status_code=204)
def delete_parcel(parcel_id: int, db: Session = Depends(get_db)) -> None:
    parcel = db.get(db_models.Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")
    db.delete(parcel)
    db.commit()
