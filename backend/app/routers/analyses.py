import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.schemas import AnalysisOut

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: uuid.UUID, db: Session = Depends(get_db)) -> AnalysisOut:
    analysis = db.get(models.Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisOut.model_validate(analysis)


@router.delete("/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    analysis = db.get(models.Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    db.delete(analysis)
    db.commit()


@router.get("/{analysis_id}/report")
def download_report(analysis_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    analysis = db.get(models.Analysis, analysis_id)
    if analysis is None or not analysis.report_pdf_data:
        raise HTTPException(status_code=404, detail="Report not found")
    return Response(
        content=analysis.report_pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="eudr-dossier-{analysis_id}.pdf"'},
    )
