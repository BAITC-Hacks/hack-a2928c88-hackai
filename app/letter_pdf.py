"""Immutable, Unicode personal recommendation PDFs; all text is XML escaped."""
import io
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether

from app.spec_pdf import register_font


LABELS = {
    "ru": {"title": "Рекомендательное письмо", "personal": "Личная копия", "role": "Роль",
        "company": "Компания", "project": "Проект", "period": "Период", "team": "Состав команды",
        "roles": "Роли указаны командой и подтверждены участниками.", "stages": "Подтверждённые этапы",
        "none": "Подтверждённых этапов нет.", "signed": "Подписант", "verify": "Проверить актуальный статус",
        "note": "Составлено из ответов заказчика по версии шаблона", "demo": "Демонстрационная учётная запись; электронная подпись не используется."},
    "kk": {"title": "Ұсыным хат", "personal": "Жеке көшірме", "role": "Рөлі",
        "company": "Компания", "project": "Жоба", "period": "Кезең", "team": "Команда құрамы",
        "roles": "Рөлдерді команда көрсетті, қатысушылар растады.", "stages": "Расталған кезеңдер",
        "none": "Расталған кезеңдер жоқ.", "signed": "Қол қоюшы", "verify": "Ағымдағы мәртебені тексеру",
        "note": "Тапсырыс берушінің жауаптарынан жасалды. Үлгі нұсқасы", "demo": "Демонстрациялық тіркелгі; электрондық қолтаңба қолданылмайды."},
    "en": {"title": "Letter of recommendation", "personal": "Personal copy", "role": "Role",
        "company": "Company", "project": "Project", "period": "Period", "team": "Team members",
        "roles": "Roles were provided by the team and confirmed by its members.", "stages": "Accepted stages",
        "none": "No accepted stages.", "signed": "Signatory", "verify": "Check current status",
        "note": "Compiled from the customer's answers. Template version", "demo": "Demonstration account; no electronic signature is used."},
}


ROLE_LABELS = {
    "analyst": {"ru": "Аналитик", "kk": "Талдаушы", "en": "Analyst"},
    "developer": {"ru": "Разработчик", "kk": "Әзірлеуші", "en": "Developer"},
    "designer": {"ru": "Дизайнер", "kk": "Дизайнер", "en": "Designer"},
    "project_manager": {"ru": "Менеджер проекта", "kk": "Жоба менеджері", "en": "Project manager"},
    "other": {"ru": "Другое", "kk": "Басқа", "en": "Other"},
}


def role_label(value, language):
    return ROLE_LABELS.get("project_manager" if value == "manager" else value, {}).get(language, value)


def recommendation_pdf(letter, member, verify_url):
    """Render frozen letter data. The URL is supplied by trusted app configuration."""
    register_font()
    labels = LABELS[letter["language"]]
    out = io.BytesIO()
    body = ParagraphStyle("LetterBody", fontName="SanaUnicode", fontSize=10, leading=14, spaceAfter=5)
    heading = ParagraphStyle("LetterHeading", parent=body, fontSize=12, leading=17,
        spaceBefore=12, textColor=colors.HexColor("#205c42"), keepWithNext=True)
    title = ParagraphStyle("LetterTitle", parent=body, fontSize=23, leading=29, spaceAfter=18)
    small = ParagraphStyle("LetterSmall", parent=body, fontSize=8, leading=11, textColor=colors.HexColor("#53665e"))
    story = []
    def paragraph(text, style=body):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)
    story.extend([paragraph("SANA HUB", heading), paragraph(labels["title"], title),
        paragraph(labels["personal"] + ": " + member["name"]),
        paragraph(labels["role"] + ": " + role_label(member["role"], letter["language"]))])
    header = letter["header"]
    for key in ("company", "project", "period"):
        value = {"company": header["company_name"], "project": header["title"],
            "period": str(header.get("started_at") or "—")[:10] + " - " + str(header.get("closed_at") or "—")[:10]}[key]
        story.append(paragraph(labels[key] + ": " + value))
    story.append(paragraph(labels["team"], heading))
    for item in letter["members"]:
        story.append(paragraph(item["name"] + " - " + role_label(item["role"], letter["language"])))
    story.append(paragraph(labels["roles"], small))
    story.append(paragraph(labels["stages"], heading))
    if not header["stages"]:
        story.append(paragraph(labels["none"]))
    for stage in header["stages"]:
        story.append(paragraph(stage["expected_result"] + " · " + stage["accepted_at"][:10]))
    story.append(Spacer(1, 12))
    story.extend(paragraph(sentence["text"]) for sentence in letter["sentences"])
    story.append(paragraph(labels["signed"], heading))
    story.extend([paragraph(letter["signer_name"] + " · " + letter["signer_position"]),
        paragraph(letter["issued_at"][:10]),
        paragraph(labels["note"] + " " + str(letter["template_version"]), small),
        paragraph(labels["demo"], small)])
    qr = QrCodeWidget(verify_url, barLevel="M")
    x, y, right, top = qr.getBounds()
    drawing = Drawing(92, 92, transform=[92/(right-x), 0, 0, 92/(top-y), 0, 0])
    drawing.add(qr)
    story.append(KeepTogether([Spacer(1, 10), paragraph(labels["verify"], heading), drawing,
        paragraph(verify_url, small)]))
    def footer(canvas, doc):
        canvas.setFont("SanaUnicode", 8)
        canvas.setFillColor(colors.HexColor("#53665e"))
        canvas.drawString(42, 24, "Sana Hub · v" + str(letter["version"]))
        canvas.drawRightString(A4[0] - 42, 24, str(doc.page))
    SimpleDocTemplate(out, pagesize=A4, leftMargin=42, rightMargin=42, topMargin=35,
        bottomMargin=44, title=labels["title"], author="Sana Hub").build(story,
        onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
