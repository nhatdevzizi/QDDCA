"""Build a polished PDF report from the validated Markdown source."""

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


DIRECTORY = Path(__file__).resolve().parent
SOURCE = DIRECTORY / "research_report_20260830_qddca_parameter_optimization.md"
FIGURE = DIRECTORY / "full_grid_tradeoffs.png"
OUTPUT = DIRECTORY.parents[1] / "output" / "pdf" / "QDDCA_parameter_optimization_report.pdf"
NAVY = colors.HexColor("#003D5C")
LIGHT = colors.HexColor("#F1F5F8")
MID = colors.HexColor("#D1D9E0")


def register_fonts():
    font_dir = Path(r"C:\Windows\Fonts")
    pdfmetrics.registerFont(TTFont("Arial", font_dir / "arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", font_dir / "arialbd.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Italic", font_dir / "ariali.ttf"))
    pdfmetrics.registerFontFamily(
        "Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic"
    )


def inline_markup(text):
    text = html.escape(text.strip())
    text = re.sub(r"`([^`]+)`", r'<font color="#003D5C">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
    text = re.sub(r"\[(\d+)\]", r'<font color="#003D5C"><b>[\1]</b></font>', text)
    return text


def styles():
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", parent=sample["Title"], fontName="Arial-Bold", fontSize=23,
            leading=28, textColor=NAVY, alignment=TA_LEFT, spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=sample["Normal"], fontName="Arial", fontSize=9,
            leading=13, textColor=colors.HexColor("#4A5568"), spaceAfter=5,
        ),
        "h1": ParagraphStyle(
            "H1", parent=sample["Heading1"], fontName="Arial-Bold", fontSize=14,
            leading=18, textColor=NAVY, spaceBefore=13, spaceAfter=8,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2", parent=sample["Heading2"], fontName="Arial-Bold", fontSize=11,
            leading=14, textColor=colors.HexColor("#1A1A1A"), spaceBefore=10,
            spaceAfter=6, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body", parent=sample["BodyText"], fontName="Arial", fontSize=9.2,
            leading=14, textColor=colors.HexColor("#222222"), spaceAfter=7,
            alignment=TA_LEFT, allowWidows=0, allowOrphans=0,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=sample["BodyText"], fontName="Arial", fontSize=9,
            leading=13, leftIndent=2, spaceAfter=3,
        ),
        "caption": ParagraphStyle(
            "Caption", parent=sample["Normal"], fontName="Arial-Italic", fontSize=8,
            leading=10, textColor=colors.HexColor("#4A5568"), alignment=TA_CENTER,
            spaceBefore=4, spaceAfter=9,
        ),
        "table": ParagraphStyle(
            "Table", parent=sample["Normal"], fontName="Arial", fontSize=7.4,
            leading=9, textColor=colors.HexColor("#222222"),
        ),
    }


def page_decor(canvas, document):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(MID)
    canvas.setLineWidth(0.5)
    canvas.line(document.leftMargin, 14 * mm, width - document.rightMargin, 14 * mm)
    canvas.setFont("Arial", 7.5)
    canvas.setFillColor(colors.HexColor("#66727B"))
    canvas.drawString(document.leftMargin, 9 * mm, "QDDCA parameter optimization")
    canvas.drawRightString(width - document.rightMargin, 9 * mm, str(document.page))
    canvas.restoreState()


def make_table(rows, style):
    data = [[Paragraph(inline_markup(cell), style["table"]) for cell in row] for row in rows]
    column_count = len(data[0])
    available = A4[0] - 34 * mm
    widths = [available / column_count] * column_count
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Arial-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, MID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def parse_markdown(text, style):
    story = []
    lines = text.splitlines()
    index = 0
    paragraph = []

    def flush_paragraph():
        if paragraph:
            joined = " ".join(part.strip() for part in paragraph)
            story.append(Paragraph(inline_markup(joined), style["body"]))
            paragraph.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            index += 1
            continue
        if stripped.startswith("![Full QDDCA parameter grid]"):
            flush_paragraph()
            image = Image(str(FIGURE))
            image._restrictSize(A4[0] - 34 * mm, 220 * mm)
            story.append(KeepTogether([
                image,
                Paragraph(
                    "Figure 1. Full new-QDDCA EDR, drop, and CV parameter surface.",
                    style["caption"],
                ),
            ]))
            index += 1
            continue
        if stripped.startswith("# "):
            flush_paragraph()
            story.append(Spacer(1, 8 * mm))
            story.append(Paragraph(inline_markup(stripped[2:]), style["title"]))
            index += 1
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            heading = stripped[3:]
            if heading == "Bibliography":
                story.append(PageBreak())
            story.append(Paragraph(inline_markup(heading.upper()), style["h1"]))
            index += 1
            continue
        if stripped.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(stripped[4:]), style["h2"]))
            index += 1
            continue
        if stripped.startswith("|") and index + 1 < len(lines) and "---" in lines[index + 1]:
            flush_paragraph()
            table_rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(set(cell) <= {"-", ":", " "} for cell in cells):
                    table_rows.append(cells)
                index += 1
            story.append(make_table(table_rows, style))
            story.append(Spacer(1, 5))
            continue
        if stripped.startswith("- "):
            flush_paragraph()
            items = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                items.append(ListItem(
                    Paragraph(inline_markup(lines[index].strip()[2:]), style["bullet"]),
                    leftIndent=10,
                ))
                index += 1
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=16, bulletFontName="Arial"))
            story.append(Spacer(1, 4))
            continue
        if stripped.startswith("**") and stripped.endswith("  "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(stripped), style["subtitle"]))
            index += 1
            continue
        paragraph.append(stripped)
        index += 1
    flush_paragraph()
    return story


def main():
    register_fonts()
    style = styles()
    document = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm,
        topMargin=16 * mm, bottomMargin=19 * mm,
        title="QDDCA Retry and Sending-Window Optimization",
        author="Codex research analysis",
    )
    story = parse_markdown(SOURCE.read_text(encoding="utf-8"), style)
    document.build(story, onFirstPage=page_decor, onLaterPages=page_decor)
    print(OUTPUT)


if __name__ == "__main__":
    main()
