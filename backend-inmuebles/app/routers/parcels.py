from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import mapping, shape
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.schemas import ParcelCreateRequest, ParcelOut, ParcelUpdateRequest

router = APIRouter(prefix="/parcels", tags=["parcels"])


def _parcel_out(parcel: models.Parcel) -> ParcelOut:
    return ParcelOut(
        id=parcel.id,
        name=parcel.name,
        address=parcel.address,
        geometry=mapping(to_shape(parcel.geom)),
        created_at=parcel.created_at,
    )


@router.post("", response_model=ParcelOut)
def create_parcel(request: ParcelCreateRequest, db: Session = Depends(get_db)) -> ParcelOut:
    geom = shape(request.geometry)
    parcel = models.Parcel(
        name=request.name,
        address=request.address,
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
def get_parcel(parcel_id: int, db: Session = Depends(get_db)) -> ParcelOut:
    parcel = db.get(models.Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")
    return _parcel_out(parcel)


@router.patch("/{parcel_id}", response_model=ParcelOut)
def update_parcel(parcel_id: int, request: ParcelUpdateRequest, db: Session = Depends(get_db)) -> ParcelOut:
    parcel = db.get(models.Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")

    parcel.name = request.name
    parcel.address = request.address
    db.commit()
    db.refresh(parcel)
    return _parcel_out(parcel)


@router.delete("/{parcel_id}", status_code=204)
def delete_parcel(parcel_id: int, db: Session = Depends(get_db)) -> None:
    parcel = db.get(models.Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")
    db.delete(parcel)
    db.commit()
