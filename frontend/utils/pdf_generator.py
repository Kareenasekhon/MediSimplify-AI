"""Professional PDF generation for MediSimplify AI report explanations."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

PAGE_WIDTH, PAGE_HEIGHT = A4
PRIMARY = colors.HexColor("#0F766E")
PRIMARY_LIGHT = colors.HexColor("#E8F7F5")
ACCENT = colors.HexColor("#2563EB")
TEXT = colors.HexColor("#172033")
MUTED = colors.HexColor("#64748B")
BORDER = colors.HexColor("#DCE7E7")
SUCCESS = colors.HexColor("#15803D")
WARNING = colors.HexColor("#B45309")
DANGER = colors.HexColor("#B91C1C")
SURFACE = colors.HexColor("#F8FAFC")

_NORMAL_STATUSES = {"normal", "within range", "within normal range", "healthy", "ok", "stable"}


def _text(value: Any, fallback: str = "Not available") -> str:
    rendered = str(value).strip() if value is not None else ""
    return rendered or fallback


def _escape(value: Any, fallback: str = "Not available") -> str:
    from xml.sax.saxutils import escape

    return escape(_text(value, fallback))


def _font_candidates(language: str) -> list[tuple[str, str, str | None]]:
    lowered = language.lower()
    if "hindi" in lowered or "हिंदी" in lowered:
        return [
            ("MSHindi", "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf", None),
            ("MSBase", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        ]
    if "punjabi" in lowered or "ਪੰਜਾਬੀ" in lowered:
        return [
            ("MSPunjabi", "/usr/share/fonts/truetype/noto/NotoSansGurmukhi-Regular.ttf", None),
            ("MSBase", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        ]
    return [
        ("MSBase", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        ("MSBase", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]


def _register_fonts(language: str) -> tuple[str, str]:
    for name, regular_path, bold_path in _font_candidates(language):
        if not Path(regular_path).exists():
            continue
        try:
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, regular_path))
            bold_name = f"{name}-Bold"
            if bold_path and Path(bold_path).exists():
                if bold_name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(bold_name, bold_path))
            else:
                bold_name = name
            return name, bold_name
        except Exception:
            continue
    return "Helvetica", "Helvetica-Bold"


def _styles(language: str) -> dict[str, ParagraphStyle]:
    regular, bold = _register_fonts(language)
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "MSTitle", parent=base["Title"], fontName=bold, fontSize=25,
            leading=31, textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "MSSubtitle", parent=base["Normal"], fontName=regular, fontSize=11,
            leading=17, textColor=MUTED, alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "MSSection", parent=base["Heading2"], fontName=bold, fontSize=14,
            leading=19, textColor=TEXT, spaceBefore=10, spaceAfter=7,
        ),
        "body": ParagraphStyle(
            "MSBody", parent=base["BodyText"], fontName=regular, fontSize=9.5,
            leading=14.5, textColor=TEXT,
        ),
        "small": ParagraphStyle(
            "MSSmall", parent=base["BodyText"], fontName=regular, fontSize=7.8,
            leading=11.5, textColor=MUTED,
        ),
        "label": ParagraphStyle(
            "MSLabel", parent=base["BodyText"], fontName=bold, fontSize=7.5,
            leading=10, textColor=PRIMARY,
        ),
        "score": ParagraphStyle(
            "MSScore", parent=base["Normal"], fontName=bold, fontSize=22,
            leading=26, textColor=PRIMARY, alignment=TA_CENTER,
        ),
        "table_header": ParagraphStyle(
            "MSTableHeader", parent=base["BodyText"], fontName=bold, fontSize=8,
            leading=11, textColor=colors.white,
        ),
        "table_body": ParagraphStyle(
            "MSTableBody", parent=base["BodyText"], fontName=regular, fontSize=7.8,
            leading=11, textColor=TEXT,
        ),
    }


def _status_style(status: Any) -> tuple[str, colors.Color]:
    raw = _text(status, "Not stated").lower()
    if raw in _NORMAL_STATUSES or "normal" in raw or "within range" in raw:
        return "Normal", SUCCESS
    if "critical" in raw or "danger" in raw:
        return _text(status), DANGER
    if any(word in raw for word in ("low", "high", "abnormal", "attention", "borderline")):
        return _text(status), WARNING
    return _text(status), MUTED


def _item_value(item: Mapping[str, Any]) -> str:
    for key in ("observed_value", "value", "result", "dosage"):
        if item.get(key) not in (None, ""):
            value = _text(item.get(key), "-")
            unit = _text(item.get("unit"), "")
            return f"{value} {unit}".strip()
    return "-"


def _visual_score(items: Sequence[Mapping[str, Any]]) -> int | None:
    if not items:
        return None
    normal = 0
    for item in items:
        raw = _text(item.get("status"), "").lower()
        if raw in _NORMAL_STATUSES or "within range" in raw or raw == "normal":
            normal += 1
    return round(normal / len(items) * 100)


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 14 * mm, PAGE_WIDTH - 18 * mm, 14 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(18 * mm, 9.5 * mm, "Generated by MediSimplify AI - Educational use only")
    canvas.drawRightString(PAGE_WIDTH - 18 * mm, 9.5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _list_block(title: str, values: Sequence[Any], styles: Mapping[str, ParagraphStyle], accent: colors.Color) -> KeepTogether | None:
    clean = [_text(v, "") for v in values if _text(v, "")]
    if not clean:
        return None
    rows = [[Paragraph(f"<b>{_escape(title)}</b>", styles["body"])]]
    rows.extend([[Paragraph(f"• {_escape(value)}", styles["body"])] for value in clean])
    table = Table(rows, colWidths=[166 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(accent.red, accent.green, accent.blue, alpha=0.08)),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.Color(accent.red, accent.green, accent.blue, alpha=0.35)),
        ("LINEBEFORE", (0, 0), (0, -1), 3, accent),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return KeepTogether([table, Spacer(1, 4 * mm)])


def generate_medical_report_pdf(
    *,
    analysis: Mapping[str, Any],
    report_type: str = "medical_report",
    language: str = "English",
    generated_at: datetime | None = None,
) -> bytes:
    """Generate and return a polished educational medical-report PDF as bytes."""
    generated_at = generated_at or datetime.now()
    styles = _styles(language)
    items = list(analysis.get("items") or [])
    score = _visual_score(items)
    report_title = _text(report_type, "Medical report").replace("_", " ").title()

    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title="MediSimplify AI Medical Report",
        author="MediSimplify AI",
        subject="AI-generated educational medical report explanation",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates(PageTemplate(id="content", frames=[frame], onPage=_footer))

    story = [Spacer(1, 18 * mm)]
    story.append(Paragraph("MediSimplify AI", styles["title"]))
    story.append(Paragraph("AI Medical Report Explanation", styles["subtitle"]))
    story.append(Spacer(1, 10 * mm))

    cover_rows = [
        [Paragraph("REPORT TYPE", styles["label"]), Paragraph(_escape(report_title), styles["body"])],
        [Paragraph("LANGUAGE", styles["label"]), Paragraph(_escape(language), styles["body"])],
        [Paragraph("GENERATED", styles["label"]), Paragraph(generated_at.strftime("%d %b %Y, %I:%M %p"), styles["body"])],
        [Paragraph("AI PROVIDER", styles["label"]), Paragraph(_escape(analysis.get("provider_used"), "Not stated"), styles["body"])],
        [Paragraph("SPECIALISED AGENT", styles["label"]), Paragraph(_escape(analysis.get("agent_used"), "Not stated").replace("_", " ").title(), styles["body"])],
    ]
    cover = Table(cover_rows, colWidths=[44 * mm, 105 * mm], hAlign="CENTER")
    cover.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.extend([cover, Spacer(1, 13 * mm)])
    story.append(Paragraph(
        "This document simplifies an uploaded medical report for educational purposes. "
        "It is not a diagnosis, prescription, or replacement for professional medical care.",
        styles["subtitle"],
    ))
    story.append(PageBreak())

    story.append(Paragraph("Report Summary", styles["section"]))
    summary_cell = Paragraph(_escape(analysis.get("summary"), "No summary was returned."), styles["body"])
    if score is not None:
        score_cell = [
            Paragraph("VALUES MARKED WITHIN RANGE", styles["label"]),
            Paragraph(f"{score}%", styles["score"]),
            Paragraph("Visual summary only - not a health or risk score.", styles["small"]),
        ]
        summary_table = Table([[summary_cell, score_cell]], colWidths=[118 * mm, 43 * mm])
    else:
        summary_table = Table([[summary_cell]], colWidths=[166 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.extend([summary_table, Spacer(1, 6 * mm)])

    story.append(Paragraph("Key Findings", styles["section"]))
    if items:
        rows = [[
            Paragraph("Parameter / Finding", styles["table_header"]),
            Paragraph("Result", styles["table_header"]),
            Paragraph("Reference / Details", styles["table_header"]),
            Paragraph("Status", styles["table_header"]),
        ]]
        status_colors: list[colors.Color] = []
        for item in items:
            status_label, status_color = _status_style(item.get("status"))
            status_colors.append(status_color)
            detail = item.get("reference_range") or item.get("simple_explanation") or item.get("section") or "-"
            rows.append([
                Paragraph(_escape(item.get("name"), "Report item"), styles["table_body"]),
                Paragraph(_escape(_item_value(item), "-"), styles["table_body"]),
                Paragraph(_escape(detail, "-"), styles["table_body"]),
                Paragraph(_escape(status_label), styles["table_body"]),
            ])
        findings = Table(rows, colWidths=[43 * mm, 32 * mm, 62 * mm, 29 * mm], repeatRows=1)
        commands = [
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
        for idx, status_color in enumerate(status_colors, start=1):
            if idx % 2 == 0:
                commands.append(("BACKGROUND", (0, idx), (-1, idx), SURFACE))
            commands.append(("TEXTCOLOR", (3, idx), (3, idx), status_color))
        findings.setStyle(TableStyle(commands))
        story.extend([findings, Spacer(1, 5 * mm)])
    else:
        story.extend([Paragraph("No structured findings were returned.", styles["body"]), Spacer(1, 5 * mm)])

    recommendations = analysis.get("recommendations") or analysis.get("important_notes") or []
    for title, values, accent in (
        ("AI Recommendations / Important Notes", recommendations, ACCENT),
        ("Unclear Information", analysis.get("unclear_information") or [], WARNING),
        ("Questions to Ask Your Doctor", analysis.get("questions_for_doctor") or [], PRIMARY),
    ):
        block = _list_block(title, values, styles, accent)
        if block:
            story.append(block)

    disclaimer = _text(
        analysis.get("disclaimer"),
        "This AI-generated explanation is for educational purposes only. Always consult a qualified medical professional before making healthcare decisions.",
    )
    story.append(Paragraph("Important Disclaimer", styles["section"]))
    disclaimer_table = Table([[Paragraph(_escape(disclaimer), styles["body"])]], colWidths=[166 * mm])
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7ED")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#FED7AA")),
        ("LINEBEFORE", (0, 0), (0, -1), 3, WARNING),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.append(disclaimer_table)

    doc.build(story)
    return buffer.getvalue()
