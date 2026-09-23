"""Unicode PDF export of exactly the reviewed specification, with no HTML execution."""
import io
import os
import re
import threading
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from app.specification import SECTIONS, SOURCE_LABELS

_font_lock = threading.Lock()


def register_font():
    with _font_lock:
        if "SanaUnicode" in pdfmetrics.getRegisteredFontNames():
            return
        candidates = [os.getenv("SPEC_PDF_FONT", ""),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf",
            "/Library/Fonts/Arial Unicode.ttf"]
        path = next((p for p in candidates if p and Path(p).is_file()), None)
        if not path:
            raise RuntimeError("Для PDF нужен шрифт с кириллицей: настройте SPEC_PDF_FONT")
        pdfmetrics.registerFont(TTFont("SanaUnicode", path))


def specification_pdf(document, *, draft=False):
    register_font()
    out = io.BytesIO()
    styles = {
        "body": ParagraphStyle("body", fontName="SanaUnicode", fontSize=10, leading=15, spaceAfter=8, splitLongWords=True),
        "heading": ParagraphStyle("heading", fontName="SanaUnicode", fontSize=13, leading=18, textColor=colors.HexColor("#205c42"), spaceBefore=14, spaceAfter=8, keepWithNext=True),
        "title": ParagraphStyle("title", fontName="SanaUnicode", fontSize=21, leading=27, spaceAfter=18),
    }
    story = []
    def paragraph(text, kind="body"):
        # Escape all customer/AI input before passing it to ReportLab's XML parser.
        clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(text))
        story.append(Paragraph(escape(clean).replace("\n", "<br/>"), styles[kind]))
    paragraph("SANA HUB · ТЕХНИЧЕСКОЕ ЗАДАНИЕ", "heading")
    paragraph(document["title"], "title")
    paragraph("ЧЕРНОВИК — не утверждён бизнесом" if draft else "Утверждено бизнесом · " + str(document.get("approved_at", "")))
    paragraph("Основа: " + ("шаблон без реального AI (mock)" if document["mode"] == "mock" else "AI / " + document["provider"]) + "; документ проверяет заказчик.")
    if document.get("synthetic"):
        paragraph("Учебные синтетические данные.")
    paragraph("1. Исходные сведения заказчика", "heading")
    for key, label in SOURCE_LABELS.items():
        paragraph(label + ": " + (document["source"].get(key) or "Не указано"))
    for number, (key, label) in enumerate(SECTIONS.items(), 2):
        paragraph(f"{number}. {label}", "heading")
        paragraph(document[key])
    paragraph("9. Идеи, выбранные заказчиком", "heading")
    if not document["ideas"]:
        paragraph("Дополнительные идеи не выбраны. Выполняется базовое ТЗ.")
    for idea in document["ideas"]:
        paragraph(idea["title"], "heading")
        for key, label in [("description", "Описание"), ("rationale", "Польза"), ("implementation", "Реализация"), ("acceptance", "Проверка результата")]:
            paragraph(label + ": " + idea[key])
    def footer(canvas, doc):
        canvas.setFont("SanaUnicode", 8)
        canvas.setFillColor(colors.HexColor("#53665e"))
        canvas.drawString(42, 25, "Sana Hub · " + ("Черновик" if draft else "Утверждённое ТЗ"))
        canvas.drawRightString(A4[0] - 42, 25, str(doc.page))
    SimpleDocTemplate(out, pagesize=A4, leftMargin=42, rightMargin=42, topMargin=38,
        bottomMargin=45, title=document["title"], author="Sana Hub").build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
