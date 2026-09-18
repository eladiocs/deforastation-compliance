"""Server-side PDF generation for the flood-risk report, mirroring the
style of the other two modules (reportlab platypus flowables, watermark logo
on the last page only)."""

import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import models

_LOGO_PATH = Path(__file__).parent / "assets" / "logo-empresa.png"
_logo_reader = ImageReader(str(_LOGO_PATH)) if _LOGO_PATH.exists() else None
_LOGO_WIDTH, _LOGO_HEIGHT = _logo_reader.getSize() if _logo_reader else (0, 0)

WATERMARK_WIDTH_FRACTION = 0.22
WATERMARK_BOTTOM_OFFSET = 0.6 * cm
WATERMARK_CONTENT_GAP = 0.5 * cm
WATERMARK_OPACITY = 0.26
_WATERMARK_WIDTH = A4[0] * WATERMARK_WIDTH_FRACTION
_WATERMARK_HEIGHT = _WATERMARK_WIDTH * (_LOGO_HEIGHT / _LOGO_WIDTH) if _logo_reader else 0
CONTENT_BOTTOM_MARGIN = WATERMARK_BOTTOM_OFFSET + _WATERMARK_HEIGHT + WATERMARK_CONTENT_GAP


def _draw_watermark(canvas: Canvas) -> None:
    if _logo_reader is None:
        return
    page_width, _ = canvas._pagesize
    x = (page_width - _WATERMARK_WIDTH) / 2
    canvas.saveState()
    canvas.setFillAlpha(WATERMARK_OPACITY)
    canvas.drawImage(_logo_reader, x, WATERMARK_BOTTOM_OFFSET, width=_WATERMARK_WIDTH, height=_WATERMARK_HEIGHT, mask="auto")
    canvas.restoreState()


class _LastPageWatermarkCanvas(Canvas):
    """Canvas that draws the watermark only on the document's final page (see
    backend-corredores/app/report_generator.py for the rationale)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for i, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            if i == num_pages - 1:
                _draw_watermark(self)
            super().showPage()
        super().save()


TEAL = colors.HexColor("#123a42")
GREEN = colors.HexColor("#5fb92c")
RED = colors.HexColor("#dc2626")
AMBER = colors.HexColor("#d97706")
GRAY = colors.HexColor("#6b7280")

RISK_LABEL_COLOR = {
    "bajo": GREEN,
    "medio": AMBER,
    "alto": RED,
    "muy_alto": RED,
}
RISK_LABEL_TEXT = {
    "bajo": "Riesgo bajo",
    "medio": "Riesgo medio",
    "alto": "Riesgo alto",
    "muy_alto": "Riesgo muy alto",
}
SEVERITY_COLOR = {"bajo": GREEN, "medio": AMBER, "alto": RED}

_styles = getSampleStyleSheet()
_styles.add(ParagraphStyle("ReportTitle", parent=_styles["Title"], textColor=TEAL, fontSize=18, spaceAfter=2))
_styles.add(ParagraphStyle("Kicker", parent=_styles["Normal"], textColor=GREEN, fontSize=9, spaceAfter=6))
_styles.add(ParagraphStyle("Meta", parent=_styles["Normal"], textColor=GRAY, fontSize=8, spaceAfter=10))
_styles.add(ParagraphStyle("H2", parent=_styles["Heading2"], textColor=TEAL, fontSize=11, spaceBefore=12, spaceAfter=4))
_styles.add(ParagraphStyle("Body", parent=_styles["Normal"], fontSize=9.5, leading=13))
_styles.add(ParagraphStyle("Footer", parent=_styles["Normal"], fontSize=7.5, textColor=GRAY))


def _score_table(analysis: models.Analysis) -> Table:
    color = RISK_LABEL_COLOR.get(analysis.risk_label, GRAY)
    label_text = RISK_LABEL_TEXT.get(analysis.risk_label, analysis.risk_label)
    data = [["Score de riesgo", "Clasificación"], [f"{analysis.risk_score:.0f} / 100", label_text]]
    table = Table(data, colWidths=[6 * cm, 6 * cm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, 0), GRAY),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("TEXTCOLOR", (1, 1), (1, 1), color),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#e5e7eb")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _factors_table(risk_factors: list[dict]) -> Table:
    label_style = ParagraphStyle("FactorLabel", parent=_styles["Body"], fontSize=9, leading=11)
    data = [["Factor", "Valor", "Severidad"]]
    for f in risk_factors:
        data.append([Paragraph(f["label"], label_style), f'{f["value"]} {f["unit"]}', f["severity"]])
    table = Table(data, colWidths=[8 * cm, 3.5 * cm, 2.5 * cm])
    style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (-1, 0), GRAY),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#e5e7eb")),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, colors.HexColor("#f3f4f6")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for row_idx, f in enumerate(risk_factors, start=1):
        color = SEVERITY_COLOR.get(f["severity"], GRAY)
        style.append(("TEXTCOLOR", (2, row_idx), (2, row_idx), color))
        style.append(("FONTNAME", (2, row_idx), (2, row_idx), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))
    return table


def generate_report_pdf(analysis: models.Analysis, parcel_name: str, address: str | None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=CONTENT_BOTTOM_MARGIN,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=f"Informe de riesgo de inundación - {parcel_name}",
    )

    story: list = [
        Paragraph("INFORME DE RIESGO DE INUNDACIÓN", _styles["Kicker"]),
        Paragraph(parcel_name, _styles["ReportTitle"]),
    ]
    if address:
        story.append(Paragraph(address, _styles["Body"]))
    meta_line = (
        f"Generado el {analysis.created_at.strftime('%d/%m/%Y %H:%M')} &middot; "
        f"Radio de análisis: {analysis.buffer_radius_m:.0f} m"
    )
    story.append(Paragraph(meta_line, _styles["Meta"]))

    story.append(Paragraph("Resultado", _styles["H2"]))
    story.append(_score_table(analysis))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Factores considerados", _styles["H2"]))
    story.append(_factors_table(analysis.risk_factors))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Metodología y fuentes de datos", _styles["H2"]))
    for note in analysis.dataset_notes:
        story.append(Paragraph(f"• {note}", _styles["Body"]))

    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            "Este informe es una herramienta de apoyo técnico y no sustituye un "
            "estudio hidrológico-hidráulico formal ni las capas oficiales de "
            "zonas inundables aplicables en la jurisdicción del inmueble.",
            _styles["Footer"],
        )
    )

    doc.build(story, canvasmaker=_LastPageWatermarkCanvas)
    return buf.getvalue()
