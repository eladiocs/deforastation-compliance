"""Server-side PDF generation for the impact-analysis report, mirroring the
content shown in ImpactReport.vue. Built with reportlab (platypus flowables)
rather than rendering the browser DOM, so the PDF looks the same regardless
of the browser's print engine."""

import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from . import db_models
from .models import ImpactAnalysisResult, ProjectMeta

# Logo como marca de agua centrada al pie de página, solo en la última página del
# documento — igual que en el informe de droughtwatch (proyecto hermano). El margen
# inferior del documento se amplía para reservarle hueco y que ningún flowable se
# le solape.
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
    canvas.drawImage(
        _logo_reader,
        x,
        WATERMARK_BOTTOM_OFFSET,
        width=_WATERMARK_WIDTH,
        height=_WATERMARK_HEIGHT,
        mask="auto",
    )
    canvas.restoreState()


class _LastPageWatermarkCanvas(Canvas):
    """Canvas that draws the watermark only on the document's final page.

    reportlab flows pages one at a time and doesn't know the total page count
    until the document finishes building, so each page's state is buffered on
    showPage() and only replayed — with the watermark added — once save() is
    called and the true last page is known.
    """

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
VIOLET = colors.HexColor("#7c3aed")
GRAY = colors.HexColor("#6b7280")

_styles = getSampleStyleSheet()
_styles.add(ParagraphStyle("ReportTitle", parent=_styles["Title"], textColor=TEAL, fontSize=18, spaceAfter=2))
_styles.add(ParagraphStyle("Kicker", parent=_styles["Normal"], textColor=GREEN, fontSize=9, spaceAfter=6))
_styles.add(ParagraphStyle("Meta", parent=_styles["Normal"], textColor=GRAY, fontSize=8, spaceAfter=10))
_styles.add(ParagraphStyle("H2", parent=_styles["Heading2"], textColor=TEAL, fontSize=11, spaceBefore=12, spaceAfter=4))
_styles.add(ParagraphStyle("H2Red", parent=_styles["H2"], textColor=RED))
_styles.add(ParagraphStyle("H2Amber", parent=_styles["H2"], textColor=AMBER))
_styles.add(ParagraphStyle("H2Violet", parent=_styles["H2"], textColor=VIOLET))
_styles.add(ParagraphStyle("Body", parent=_styles["Normal"], fontSize=9.5, leading=13))
_styles.add(ParagraphStyle("ReportBullet", parent=_styles["Body"], leftIndent=12, spaceAfter=2))
_styles.add(ParagraphStyle("Footer", parent=_styles["Normal"], fontSize=7.5, textColor=GRAY))

LEGEND_ITEMS = [
    (TEAL, "Parche de hábitat que sobrevive en el escenario con proyecto."),
    (RED, "Parche de hábitat perdido — su área se solapa con la huella del proyecto."),
    (AMBER, "Parche recién aislado — sobrevive, pero se quedó sin ninguna ruta de dispersión viable."),
    (GREEN, "Corredor sin afectar — su costo no cambió de forma significativa."),
    (VIOLET, "Corredor cortado — uno de los parches que conectaba fue destruido, o ya no existe ruta equivalente."),
]


def _swatch(color: colors.Color) -> Table:
    t = Table([[""]], colWidths=[0.35 * cm], rowHeights=[0.35 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), color), ("BOX", (0, 0), (0, 0), 0.5, colors.white)]))
    return t


def _legend_section() -> list:
    story: list = [Paragraph("Cómo interpretar este informe", _styles["H2"])]
    rows = [[_swatch(color), Paragraph(text, _styles["Body"])] for color, text in LEGEND_ITEMS]
    table = Table(rows, colWidths=[0.9 * cm, None])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "Un <b>parche recién aislado</b> es un parche que no fue destruido directamente por el proyecto, "
            "pero que quedó sin ninguna ruta de dispersión viable tras su construcción — suele ser la señal de "
            "impacto más crítica, porque puede aislar una población incluso sin ocupar su hábitat.",
            _styles["Body"],
        )
    )
    return story


def _connectivity_table(result: ImpactAnalysisResult) -> Table:
    baseline, scenario = result.baseline.metrics, result.scenario.metrics
    data = [
        ["Métrica", "Antes", "Después"],
        ["Parches de hábitat", str(baseline.total_patches), str(scenario.total_patches)],
        ["Corredores", str(baseline.total_corridors), str(scenario.total_corridors)],
    ]
    table = Table(data, colWidths=[7 * cm, 4 * cm, 4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, 0), GRAY),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#e5e7eb")),
                ("LINEBELOW", (0, 1), (-1, -2), 0.5, colors.HexColor("#f3f4f6")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )
    return table


def generate_report_pdf(analysis: db_models.Analysis, parcel_name: str) -> bytes:
    result = ImpactAnalysisResult(**analysis.result)
    project_meta = ProjectMeta(**analysis.project_meta)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=CONTENT_BOTTOM_MARGIN,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=f"Informe de impacto - {parcel_name}",
    )

    names = {p.id: p.name for p in result.patches}
    story: list = [
        Paragraph("INFORME DE IMPACTO", _styles["Kicker"]),
        Paragraph(parcel_name, _styles["ReportTitle"]),
    ]
    if project_meta.description:
        story.append(Paragraph(project_meta.description, _styles["Body"]))
    meta_line = f"Generado el {analysis.created_at.strftime('%d/%m/%Y %H:%M')}"
    if project_meta.prepared_by:
        meta_line += f" &middot; Elaborado por {project_meta.prepared_by}"
    story.append(Paragraph(meta_line, _styles["Meta"]))

    story.append(Paragraph("Metodología y supuestos", _styles["H2"]))
    story.append(Paragraph(f"Distancia de dispersión considerada: {analysis.dispersal_label}.", _styles["ReportBullet"]))
    story.append(
        Paragraph(
            "Los datos de cobertura de suelo y zonas verdes combinan el mapa satelital ESA WorldCover (10 m, 2021) "
            "como fuente principal con datos de OpenStreetMap (caminos, cursos de agua y nombres de sitios). Ambas "
            "fuentes pueden no reflejar el estado actual del terreno (por ejemplo, WorldCover puede confundir "
            "plantaciones con bosque natural o no reflejar deforestación posterior a 2021), por lo que se recomienda "
            "validación de campo antes de su uso en un expediente formal.",
            _styles["ReportBullet"],
        )
    )

    story.append(Paragraph("Conectividad antes / después", _styles["H2"]))
    story.append(_connectivity_table(result))

    if result.patches_lost:
        story.append(Paragraph("Parches de hábitat perdidos", _styles["H2Red"]))
        for p in result.patches_lost:
            story.append(Paragraph(f"• {p.name}", _styles["ReportBullet"]))

    if result.corridors_lost:
        story.append(Paragraph("Corredores cortados", _styles["H2Violet"]))
        for e in result.corridors_lost:
            source = names.get(e.source, e.source)
            target = names.get(e.target, e.target)
            story.append(Paragraph(f"• {source} ↔ {target}", _styles["ReportBullet"]))

    if result.newly_isolated_patch_ids:
        story.append(Paragraph("Parches recién aislados", _styles["H2Amber"]))
        joined = ", ".join(names.get(pid, pid) for pid in result.newly_isolated_patch_ids)
        story.append(Paragraph(joined, _styles["Body"]))

    story.extend(_legend_section())

    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            "Este informe es una herramienta de apoyo técnico y no sustituye el criterio profesional ni la "
            "validación de campo requerida para un Estudio de Impacto Ambiental formal.",
            _styles["Footer"],
        )
    )

    doc.build(story, canvasmaker=_LastPageWatermarkCanvas)
    return buf.getvalue()
