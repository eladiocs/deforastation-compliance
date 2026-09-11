import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.schemas import AnalysisOut
from app.storage import delete_report_pdf

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

    delete_report_pdf(analysis.report_pdf_path)
    db.delete(analysis)
    db.commit()


@router.get("/{analysis_id}/report")
def download_report(analysis_id: uuid.UUID, db: Session = Depends(get_db)) -> FileResponse:
    analysis = db.get(models.Analysis, analysis_id)
    if analysis is None or not analysis.report_pdf_path:
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(
        analysis.report_pdf_path,
        media_type="application/pdf",
        filename=f"eudr-dossier-{analysis_id}.pdf",
    )
