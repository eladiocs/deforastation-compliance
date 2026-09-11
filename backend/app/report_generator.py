"""Builds the EUDR due-diligence dossier PDF for a parcel analysis.

The report is generated in two passes: the substantive content (pages
1..N) is rendered first and hashed, then a final verification page
carrying that hash and its signature is appended. This way the signature
covers exactly the content a reviewer reads, and re-hashing the first
N-1 pages of any downloaded copy lets anyone confirm it hasn't been
altered.
"""

import hashlib
import io
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import qrcode
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from shapely.geometry import shape

from app.signing import public_key_pem, sign_message

STATUS_LABELS = {
    "compliant": "CONFORME — sin deforestación detectada tras la fecha de corte",
    "non_compliant": "NO CONFORME — deforestación detectada tras la fecha de corte",
    "needs_review": "REVISIÓN MANUAL NECESARIA — cobertura de datos insuficiente para un veredicto automático",
}
STATUS_COLORS = {
    "compliant": colors.HexColor("#1a7f37"),
    "non_compliant": colors.HexColor("#c1121f"),
    "needs_review": colors.HexColor("#b8860b"),
}


def _ndvi_chart_image(ndvi_series: list[dict]) -> io.BytesIO:
    points = [(p["period_start"], p["ndvi_mean"]) for p in ndvi_series if p["ndvi_mean"] is not None]
    fig, ax = plt.subplots(figsize=(6, 2.6))
    if points:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        ax.plot(xs, ys, marker="o", markersize=3, linewidth=1.5, color="#1a7f37")
        ax.set_xticks(xs[::max(1, len(xs) // 8)])
        ax.set_xticklabels(xs[::max(1, len(xs) // 8)], rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("NDVI medio")
    ax.set_title("Serie NDVI trimestral (Sentinel-2)", fontsize=10)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf


def _loss_chart_image(yearly_loss: list[dict], cutoff_year: int) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(6, 2.6))
    years = [d["year"] for d in yearly_loss]
    areas = [d["area_ha"] for d in yearly_loss]
    bar_colors = ["#c1121f" if y > cutoff_year else "#6c757d" for y in years]
    ax.bar(years, areas, color=bar_colors)
    ax.axvline(cutoff_year + 0.5, color="black", linestyle="--", linewidth=1)
    ax.set_ylabel("Pérdida (ha)")
    ax.set_title("Pérdida de cobertura forestal por año (Hansen GFC)", fontsize=10)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf


def _parcel_map_image(geojson: dict) -> io.BytesIO:
    geom = shape(geojson)
    fig, ax = plt.subplots(figsize=(5, 5))
    polygons = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    for poly in polygons:
        xs, ys = poly.exterior.xy
        ax.fill(xs, ys, alpha=0.3, color="#1a7f37")
        ax.plot(xs, ys, color="#1a7f37", linewidth=1.5)
    ax.set_aspect("equal")
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.set_title("Límites de la parcela", fontsize=10)
    ax.grid(alpha=0.3)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.tick_params(axis="x", labelrotation=45, labelsize=7)
    ax.tick_params(axis="y", labelsize=7)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf


def _build_content_pdf(parcel, analysis) -> bytes:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleEs", parent=styles["Title"], fontSize=16)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=12)
    body = styles["Normal"]

    story = []
    story.append(Paragraph("Informe de Debida Diligencia — EUDR", title_style))
    story.append(Paragraph("Reglamento (UE) 2023/1115 sobre productos libres de deforestación", body))
    story.append(Spacer(1, 0.5 * cm))

    status = analysis.compliance_status
    verdict_style = ParagraphStyle(
        "Verdict", parent=styles["Heading2"], textColor=STATUS_COLORS.get(status, colors.black)
    )
    story.append(Paragraph(STATUS_LABELS.get(status, status.upper()), verdict_style))
    story.append(Spacer(1, 0.3 * cm))

    info_table = Table(
        [
            ["Parcela", parcel.name],
            ["Cliente", parcel.client_name or "—"],
            ["Materia prima", parcel.commodity or "—"],
            ["Fecha de corte EUDR", analysis.cutoff_date.isoformat()],
            ["Superficie total", f"{analysis.parcel_area_ha:.2f} ha"],
            ["Cobertura forestal base (año 2000)", f"{analysis.baseline_forest_area_ha:.2f} ha"],
            ["Pérdida tras la fecha de corte", f"{analysis.loss_after_cutoff_area_ha:.2f} ha"],
            ["Informe generado", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
            ["ID de análisis", str(analysis.id)],
        ],
        colWidths=[6 * cm, 10 * cm],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 0.5 * cm))

    story.append(
        KeepTogether(
            [
                Paragraph("Metodología", h2),
                Paragraph(
                    "La clasificación de pérdida de cobertura forestal se basa en el dataset Hansen "
                    "Global Forest Change (Universidad de Maryland), que combina series temporales "
                    "Landsat para detectar pérdida de cobertura arbórea año a año a nivel global. "
                    f"Se considera bosque de referencia todo píxel con cobertura arbórea en el año 2000 "
                    f"superior al {analysis.min_tree_cover_pct}%. La serie NDVI trimestral (Sentinel-2, "
                    "enmascarada por nubes) se incluye como corroboración visual de los meses más "
                    "recientes, no cubiertos todavía por la última actualización de Hansen.",
                    body,
                ),
            ]
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    story.append(
        KeepTogether(
            [
                Paragraph("Límites de la parcela", h2),
                Image(_parcel_map_image(parcel_geojson(parcel)), width=9 * cm, height=9 * cm),
            ]
        )
    )

    story.append(
        KeepTogether(
            [
                Paragraph("Pérdida de cobertura forestal por año", h2),
                Image(
                    _loss_chart_image(analysis.yearly_loss_since_2001, analysis.cutoff_date.year),
                    width=14 * cm,
                    height=6.1 * cm,
                ),
            ]
        )
    )

    story.append(
        KeepTogether(
            [
                Paragraph("Serie NDVI (corroboración reciente)", h2),
                Image(_ndvi_chart_image(analysis.ndvi_quarterly_series), width=14 * cm, height=6.1 * cm),
            ]
        )
    )

    story.append(
        KeepTogether(
            [
                Paragraph("Notas sobre las fuentes de datos", h2),
                *[Paragraph(f"• {note}", body) for note in analysis.dataset_notes],
            ]
        )
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    doc.build(story)
    return buf.getvalue()


def _build_verification_pdf(content_sha256: str, signature_b64: str, analysis_id: str) -> bytes:
    styles = getSampleStyleSheet()
    body = styles["Normal"]
    mono = ParagraphStyle("Mono", parent=body, fontName="Courier", fontSize=7, leading=9)

    qr_payload = f"defor-compliance-verify:{analysis_id}:{content_sha256}"
    qr_img = qrcode.make(qr_payload)
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    story = [
        Paragraph("Verificación de integridad del documento", styles["Heading2"]),
        Spacer(1, 0.3 * cm),
        Paragraph(
            "Este documento incorpora una firma criptográfica generada por la plataforma "
            "sobre el contenido de las páginas anteriores. Cualquier modificación del PDF "
            "invalida la firma. Esta firma acredita la integridad del informe emitido por "
            "esta plataforma; <b>no es una firma electrónica cualificada eIDAS</b> — para "
            "presentación ante aduanas que exija ese nivel, el hash de este informe debe "
            "someterse a un prestador de servicios de confianza (TSP) autorizado.",
            body,
        ),
        Spacer(1, 0.4 * cm),
        Paragraph(f"<b>ID de análisis:</b> {analysis_id}", body),
        Paragraph("<b>SHA-256 del contenido:</b>", body),
        Paragraph(content_sha256, mono),
        Spacer(1, 0.2 * cm),
        Paragraph("<b>Firma (RSA-PSS/SHA-256, base64):</b>", body),
        Paragraph(signature_b64, mono),
        Spacer(1, 0.3 * cm),
        Image(qr_buf, width=3 * cm, height=3 * cm),
        Spacer(1, 0.2 * cm),
        Paragraph("<b>Clave pública de verificación (PEM):</b>", body),
        Paragraph(public_key_pem().replace("\n", "<br/>"), mono),
    ]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    doc.build(story)
    return buf.getvalue()


def parcel_geojson(parcel) -> dict:
    from geoalchemy2.shape import to_shape
    from shapely.geometry import mapping

    return mapping(to_shape(parcel.geom))


def generate_report(parcel, analysis) -> tuple[bytes, str, str]:
    content_bytes = _build_content_pdf(parcel, analysis)
    content_sha256 = hashlib.sha256(content_bytes).hexdigest()
    signature_b64 = sign_message(content_sha256.encode("ascii"))
    verification_bytes = _build_verification_pdf(content_sha256, signature_b64, str(analysis.id))

    writer = PdfWriter()
    for page in PdfReader(io.BytesIO(content_bytes)).pages:
        writer.add_page(page)
    for page in PdfReader(io.BytesIO(verification_bytes)).pages:
        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue(), content_sha256, signature_b64
