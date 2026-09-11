import os
import uuid

from app.config import settings


def save_report_pdf(analysis_id: uuid.UUID, pdf_bytes: bytes) -> str:
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    path = os.path.join(settings.REPORTS_DIR, f"{analysis_id}.pdf")
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return path


def delete_report_pdf(path: str | None) -> None:
    if not path:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
