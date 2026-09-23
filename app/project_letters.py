"""Project assessment and immutable, evidence-linked recommendation letters.

All authorisation uses the server-resolved community actor. The demonstration
session is not production identity verification and issued PDFs say so.
"""
import base64
import copy
import hashlib
import html
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import Field, field_validator

from app.letter_pdf import recommendation_pdf, role_label
from app.schemas import Model, NonEmpty
from app.stages import stage_key
from app.store import Store


def now():
    return datetime.now(timezone.utc)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


class _Plain(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.blocked = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "iframe", "object"):
            self.blocked += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "iframe", "object"):
            self.blocked = max(0, self.blocked - 1)

    def handle_data(self, text):
        if not self.blocked:
            self.parts.append(text)


def plain(value):
    value = str(value)
    if len(value) > 30000:
        raise ValueError("Текст слишком длинный")
    for _ in range(8):
        decoded = html.unescape(value)
        if decoded == value:
            break
        value = decoded
    parser = _Plain()
    parser.feed(value)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff]", "", "".join(parser.parts)).strip()


def labels(ru, kk, en):
    return {"ru": ru, "kk": kk, "en": en}


def option(value, ru, kk, en, phrase=None):
    label = labels(ru, kk, en)
    return {"value": value, "label": label, "label_ru": ru, "label_kk": kk,
        "phrase": labels(*phrase) if phrase else label}


EXPECTATIONS = [
    option("below", "Ниже ожиданий", "Күткеннен төмен", "Below expectations"),
    option("meets", "Соответствует", "Сәйкес келеді", "Meets expectations"),
    option("exceeds", "Превзошёл", "Күткеннен жоғары", "Exceeds expectations"),
]


def question(id, ru, kk, en, options=None, type="single", **kwargs):
    return {"id": id, "label": labels(ru, kk, en), "label_ru": ru, "label_kk": kk,
        "type": type, "options": options or [], **kwargs}


TEMPLATE = {"version": "1", "languages": ["ru", "kk", "en"], "questions": [
    question("q1", "Насколько результат соответствует ожидаемому из карточки?",
        "Нәтиже карточкадағы күтілімге қаншалықты сәйкес келеді?", "How does the result compare with the card's expectations?", EXPECTATIONS),
    question("q2", "Что сделала команда?", "Команда не істеді?", "What did the team deliver?", [
        option("data", "Собрала и проанализировала данные", "Деректерді жинап, талдады", "Collected and analysed data"),
        option("prototype", "Разработала прототип", "Прототип жасады", "Developed a prototype"),
        option("interface", "Спроектировала интерфейс", "Интерфейсті жобалады", "Designed the interface"),
        option("testing", "Провела тестирование", "Тестілеу өткізді", "Performed testing"),
        option("presentation", "Представила результат", "Нәтижені ұсынды", "Presented the result"),
        option("other", "Другое", "Басқа", "Other work"),
    ], type="multiple", max_choices=6, required_comment=True, comment_min_length=50, comment_max_length=500),
    question("q3", "Сильные стороны команды (до 3)", "Команданың мықты жақтары (3-ке дейін)", "Team strengths (up to 3)", [
        option("responsibility", "Ответственность", "Жауапкершілік", "Responsibility"),
        option("independence", "Самостоятельность", "Дербестік", "Independence"),
        option("initiative", "Инициативность", "Бастамашылдық", "Initiative"),
        option("learning", "Обучаемость", "Үйренуге қабілеттілік", "Ability to learn"),
        option("communication", "Коммуникация", "Қарым-қатынас", "Communication"),
        option("analysis", "Аналитическое мышление", "Аналитикалық ойлау", "Analytical thinking"),
    ], type="multiple", max_choices=3),
    question("q4", "Как команда соблюдала договорённости?", "Команда келісімдерді қалай орындады?", "How did the team honour its commitments?", EXPECTATIONS),
    question("q5", "Что будет с прототипом?", "Прототиппен не болады?", "What will happen to the prototype?", [
        option("implementing", "Внедряем", "Енгізіп жатырмыз", "Implementing"),
        option("testing", "Тестируем", "Сынап жатырмыз", "Testing"),
        option("not_planned", "Пока не планируем", "Әзірге жоспар жоқ", "No current plans"),
    ]),
    question("q6", "Готовы рекомендовать команду?", "Команданы ұсынуға дайынсыз ба?", "Would you recommend the team?", [
        option("unreserved", "Да, без оговорок", "Иә, толық сеніммен", "Yes, without reservation"),
        option("yes", "Да", "Иә", "Yes"), option("no", "Нет", "Жоқ", "No"),
    ]),
    question("q7", "Готовы рассмотреть участников на стажировку или работу?", "Қатысушыларды тағылымдамаға немесе жұмысқа қарастыруға дайынсыз ба?", "Would you consider members for an internship or a job?", [
        option("yes", "Да", "Иә", "Yes"), option("maybe", "Возможно", "Мүмкін", "Possibly"), option("no", "Нет", "Жоқ", "No"),
    ]),
    question("q8", "Хотите отметить кого-то отдельно?", "Біреуді жеке атап өткіңіз келе ме?", "Would you like to highlight a member?", type="highlight", max_choices=2),
    question("q9", "Что ещё хотите сказать?", "Тағы не айтқыңыз келеді?", "Any other comments?", type="text", comment_max_length=1000),
], "phrases": {
    "q1": labels("Результат относительно ожиданий: {value}.", "Нәтиженің күтілімге сәйкестігі: {value}.", "Result against expectations: {value}."),
    "q2": labels("Выполненная работа: {value}.", "Орындалған жұмыс: {value}.", "Work delivered: {value}."),
    "q3": labels("Сильная сторона команды: {value}.", "Команданың мықты жағы: {value}.", "A team strength: {value}."),
    "q4": labels("Соблюдение договорённостей: {value}.", "Келісімдерді орындауы: {value}.", "Commitments honoured: {value}."),
    "q5": labels("Дальнейшие планы на прототип: {value}.", "Прототипке қатысты алдағы жоспар: {value}.", "Plans for the prototype: {value}."),
    "q6": labels("Готовность рекомендовать команду: {value}.", "Команданы ұсынуға дайындық: {value}.", "Willingness to recommend the team: {value}."),
    "q7": labels("Готовность рассмотреть участников на стажировку или работу: {value}.", "Қатысушыларды тағылымдамаға немесе жұмысқа қарастыру: {value}.", "Willingness to consider members for an internship or job: {value}."),
    "q8": labels("Заказчик отдельно отметил: {value}.", "Тапсырыс беруші жеке атап өтті: {value}.", "The customer highlighted: {value}."),
}}


class CloseInput(Model):
    status: Literal["completed", "closed_early"]


class MemberInput(Model):
    user_id: NonEmpty = Field(max_length=200)
    role: NonEmpty = Field(max_length=100)

    @field_validator("role", mode="before")
    @classmethod
    def clean_role(cls, value):
        return plain(value)


class RolesInput(Model):
    members: list[MemberInput] = Field(max_length=50)


class ConfirmRoleInput(Model):
    expected_role: NonEmpty = Field(max_length=100)


class AssessmentInput(Model):
    answers: dict[str, str | list[str]]
    comments: dict[str, str] = Field(default_factory=dict)
    highlighted_user_ids: list[str] = Field(default_factory=list, max_length=2)

    @field_validator("comments", mode="before")
    @classmethod
    def clean_comments(cls, value):
        return {key: plain(text) for key, text in value.items()} if isinstance(value, dict) else value


class SignInput(Model):
    signer_name: NonEmpty = Field(max_length=160)
    signer_position: NonEmpty = Field(max_length=160)

    @field_validator("signer_name", "signer_position", mode="before")
    @classmethod
    def clean_signer(cls, value):
        return plain(value)


class ReissueInput(SignInput):
    draft_id: NonEmpty = Field(max_length=100)
    language: Literal["ru", "kk", "en"] = "ru"


class ReasonInput(Model):
    reason: NonEmpty = Field(max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def clean_reason(cls, value):
        return plain(value)


class ComplaintInput(Model):
    text: NonEmpty = Field(max_length=2000)

    @field_validator("text", mode="before")
    @classmethod
    def clean_text(cls, value):
        return plain(value)


class VisibilityInput(Model):
    show_in_portfolio: bool


class ConsentInput(Model):
    public_consent: bool


def register_project_letters(app, store, require, actor, owner, audit, notify):
    with store.transaction() as db:
        if not Store.get(db, "questionnaire_template", TEMPLATE["version"]):
            Store.put(db, "questionnaire_template", TEMPLATE["version"], TEMPLATE)

    def owns(db, project, user):
        owner(db, require(db, "card", project["task_id"]), user)

    def captain(project, user):
        return user.get("role") == "student" and user.get("team_id") == project["team_id"] and user.get("captain") is True

    def view_allowed(db, project, user):
        if user.get("role") == "moderator" or (user.get("role") == "student" and user.get("team_id") == project["team_id"]):
            return
        owns(db, project, user)

    def is_owner(project, user):
        return user.get("role") == "business" and user.get("company_id") == project["company_id"]

    def members(db, project):
        return [r for r in Store.all(db, "team_member_role") if r["project_id"] == project["id"]]

    def deadline(project):
        return (timestamp(project["closed_at"]) + timedelta(days=30)).isoformat() if project.get("closed_at") else None

    def assessment_open(project):
        if project["status"] not in ("completed", "closed_early"):
            raise HTTPException(409, "Опросник доступен после завершения или досрочного закрытия проекта")
        if now() > timestamp(deadline(project)):
            raise HTTPException(410, "30-дневное окно опросника завершено")

    def copy_view(item):
        return {key: value for key, value in item.items() if key != "pdf_base64"}

    def letter_view(db, letter, user=None):
        value = copy.deepcopy(letter)
        copies = [c for c in Store.all(db, "letter_copy") if c["letter_id"] == letter["id"]]
        if user and user.get("role") == "student":
            value.pop("assessment_snapshot", None)
            copies = [c for c in copies if c["student_user_id"] == user["id"]]
        value["copies"] = [copy_view(c) for c in copies]
        return value

    def project_view(db, project, user):
        value = copy.deepcopy(project)
        value["members"] = members(db, project)
        value["available_members"] = [{"id": u["id"], "name": u["name"]} for u in Store.all(db, "user")
            if u.get("role") == "student" and u.get("team_id") == project["team_id"]]
        value["assessment_deadline"] = deadline(project)
        can_assess = is_owner(project, user) and bool(project.get("closed_at")) and now() <= timestamp(deadline(project))
        value["permissions"] = {"can_manage_roles": captain(project, user) and project["status"] == "active",
            "can_close": is_owner(project, user) and project["status"] == "active", "can_assess": can_assess,
            "can_confirm_role": user.get("role") == "student" and project["status"] == "active" and any(
                r["user_id"] == user["id"] and not r.get("confirmed_at") for r in value["members"]),
            "can_consent": captain(project, user), "can_revoke": is_owner(project, user)}
        # Raw assessment responses belong to the customer, not the public team profile.
        value["assessment"] = Store.get(db, "project_assessment", project["id"]) if is_owner(project, user) or user.get("role") == "moderator" else None
        value["letters"] = [letter_view(db, letter, user) for letter in Store.all(db, "recommendation_letter") if letter["project_id"] == project["id"]]
        value["letters"].sort(key=lambda letter: letter["version"], reverse=True)
        value["copies"] = [c for letter in value["letters"] for c in letter["copies"]]
        return value

    def project_id(proposal):
        pair = json.dumps([proposal["task_id"], proposal["team_id"]], ensure_ascii=False)
        return "project-" + hashlib.sha256(pair.encode()).hexdigest()[:24]

    @app.post("/api/proposals/{id}/project", status_code=201)
    def create_project(id: str, user=Depends(actor)):
        with store.transaction() as db:
            proposal = require(db, "proposal", id)
            card = require(db, "card", proposal["task_id"])
            stub = {"team_id": proposal["team_id"]}
            if not captain(stub, user):
                owner(db, card, user)
            if proposal["status"] != "selected":
                raise HTTPException(409, "Сначала бизнес должен выбрать команду")
            pid = project_id(proposal)
            project = Store.get(db, "project", pid)
            if not project:
                company_id = card.get("company_id", "demo-company")
                company = next((u for u in Store.all(db, "user") if u.get("role") == "business" and u.get("company_id") == company_id), {})
                stage = Store.get(db, "stage", stage_key(proposal))
                project = {"id": pid, "proposal_id": id, "task_id": proposal["task_id"], "team_id": proposal["team_id"],
                    "company_id": company_id, "company_name": plain(card.get("company_name") or company.get("company_name") or company_id),
                    "owner_user_id": company.get("id"), "title": plain((card.get("snapshot") or card["card"]).get("title", "")),
                    "status": "active", "started_at": stage.get("created_at") if stage else None,
                    "created_at": now().isoformat(), "closed_at": None, "public_consent": False}
                Store.put(db, "project", pid, project)
                audit(db, "project_created", user["id"], pid, {"proposal_id": id})
            return project_view(db, project, user)

    @app.get("/api/proposals/{id}/project")
    def proposal_project(id: str, user=Depends(actor)):
        with store.transaction() as db:
            proposal = require(db, "proposal", id)
            project = require(db, "project", project_id(proposal))
            view_allowed(db, project, user)
            return project_view(db, project, user)

    @app.get("/api/projects")
    def list_projects(user=Depends(actor)):
        with store.transaction() as db:
            projects = [p for p in Store.all(db, "project") if user.get("role") == "moderator" or is_owner(p, user)
                or (user.get("role") == "student" and user.get("team_id") == p["team_id"])]
            return [project_view(db, p, user) for p in projects]

    @app.get("/api/projects/{id}")
    def get_project(id: str, user=Depends(actor)):
        with store.transaction() as db:
            project = require(db, "project", id)
            view_allowed(db, project, user)
            return project_view(db, project, user)

    @app.put("/api/projects/{id}/roles")
    def set_roles(id: str, body: RolesInput, user=Depends(actor)):
        with store.transaction() as db:
            project = require(db, "project", id)
            if not captain(project, user):
                raise HTTPException(403, "Состав и роли указывает капитан этой команды")
            if project["status"] != "active":
                raise HTTPException(409, "После завершения проекта состав и роли зафиксированы")
            ids = [member.user_id for member in body.members]
            if len(ids) != len(set(ids)):
                raise HTTPException(422, "Участник указан дважды")
            current = {r["user_id"]: r for r in members(db, project)}
            updates = []
            for member in body.members:
                person = require(db, "user", member.user_id)
                if person.get("role") != "student" or person.get("team_id") != project["team_id"]:
                    raise HTTPException(422, "В состав можно включить только участников этой команды")
                old = current.get(member.user_id, {})
                updates.append({"project_id": id, "user_id": member.user_id, "student_user_id": member.user_id,
                    "name": plain(person["name"]), "role": member.role,
                    "confirmed_at": old.get("confirmed_at") if old.get("role") == member.role else None})
            for user_id in current.keys() - set(ids):
                db.execute("DELETE FROM records WHERE kind=? AND id=?", ("team_member_role", json.dumps([id, user_id])))
            for member in updates:
                Store.put(db, "team_member_role", json.dumps([id, member["user_id"]]), member)
            audit(db, "project_roles_updated", user["id"], id, {"user_ids": ids})
            return project_view(db, project, user)

    @app.post("/api/projects/{id}/roles/confirm")
    def confirm_role(id: str, body: ConfirmRoleInput, user=Depends(actor)):
        with store.transaction() as db:
            project = require(db, "project", id)
            if user.get("role") != "student" or user.get("team_id") != project["team_id"]:
                raise HTTPException(403, "Можно подтвердить только свою роль в своей команде")
            if project["status"] != "active":
                raise HTTPException(409, "Роли подтверждаются до завершения проекта")
            key = json.dumps([id, user["id"]])
            member = require(db, "team_member_role", key)
            if member["role"] != body.expected_role:
                raise HTTPException(409, "Капитан изменил вашу роль. Обновите состав и проверьте роль перед подтверждением.")
            if not member["confirmed_at"]:
                member["confirmed_at"] = now().isoformat()
                Store.put(db, "team_member_role", key, member)
                audit(db, "project_role_confirmed", user["id"], id)
            return project_view(db, project, user)

    @app.post("/api/projects/{id}/close")
    def close_project(id: str, body: CloseInput, user=Depends(actor)):
        with store.transaction() as db:
            project = require(db, "project", id)
            owns(db, project, user)
            if project["status"] != "active":
                if project["status"] != body.status:
                    raise HTTPException(409, "Проект уже закрыт с другим статусом")
                return project_view(db, project, user)
            if body.status == "completed":
                stage = Store.get(db, "stage", stage_key(project))
                if not stage or stage.get("status") != "accepted" or not stage.get("decided_at"):
                    raise HTTPException(409, "Для завершения требуется принятый этап, а не баллы прогресса")
            project.update(status=body.status, closed_at=now().isoformat())
            Store.put(db, "project", id, project)
            audit(db, "project_closed", user["id"], id, {"status": body.status})
            return project_view(db, project, user)

    @app.get("/api/projects/{id}/questionnaire")
    def questionnaire(id: str, user=Depends(actor)):
        with store.transaction() as db:
            project = require(db, "project", id)
            owns(db, project, user)
            assessment_open(project)
            assessment = Store.get(db, "project_assessment", id)
            version = assessment["template_version"] if assessment else TEMPLATE["version"]
            return {"template": require(db, "questionnaire_template", version), "assessment": assessment,
                "available": True, "deadline": deadline(project), "members": [r for r in members(db, project) if r["confirmed_at"]]}

    @app.put("/api/projects/{id}/assessment")
    def save_assessment(id: str, body: AssessmentInput, user=Depends(actor)):
        with store.transaction() as db:
            project = require(db, "project", id)
            owns(db, project, user)
            assessment_open(project)
            old = Store.get(db, "project_assessment", id)
            template = require(db, "questionnaire_template", old["template_version"] if old else TEMPLATE["version"])
            if set(body.answers) != {"q1", "q2", "q3", "q4", "q5", "q6", "q7"}:
                raise HTTPException(422, "Нужны ответы q1–q7; участники и комментарии передаются отдельно")
            for q in template["questions"][:7]:
                value = body.answers[q["id"]]
                choices = {o["value"] for o in q["options"]}
                if q["type"] == "multiple":
                    if not isinstance(value, list) or len(value) > q["max_choices"] or len(value) != len(set(value)) or set(value) - choices:
                        raise HTTPException(422, "Недопустимый выбор: " + q["id"])
                    if q["id"] == "q2" and not value:
                        raise HTTPException(422, "Укажите выполненную работу в вопросе 2")
                elif not isinstance(value, str) or value not in choices:
                    raise HTTPException(422, "Недопустимый ответ: " + q["id"])
            if set(body.comments) - {"q" + str(i) for i in range(1, 10)}:
                raise HTTPException(422, "Неизвестный комментарий")
            if not 50 <= len(body.comments.get("q2", "")) <= 500:
                raise HTTPException(422, "В вопросе 2 нужен конкретный пример результата: 50–500 символов")
            if any(len(text) > 1000 for text in body.comments.values()):
                raise HTTPException(422, "Комментарий не может быть длиннее 1000 символов")
            confirmed = {r["user_id"] for r in members(db, project) if r["confirmed_at"]}
            if len(body.highlighted_user_ids) != len(set(body.highlighted_user_ids)) or set(body.highlighted_user_ids) - confirmed:
                raise HTTPException(422, "Отметить можно только участников с подтверждённой ролью")
            assessment = {"project_id": id, "template_version": template["version"], **body.model_dump(),
                "public_consent": project["public_consent"], "revision": (old or {}).get("revision", 0) + 1,
                "submitted_at": now().isoformat(), "submitted_by": user["id"]}
            Store.put(db, "project_assessment", id, assessment)
            audit(db, "project_assessment_submitted", user["id"], id, {"revision": assessment["revision"]})
            return assessment

    def assemble(db, project, language):
        assessment = require(db, "project_assessment", project["id"])
        if assessment["answers"]["q6"] == "no":
            raise HTTPException(409, "Заказчик не готов рекомендовать команду: письмо не формируется")
        confirmed = [r for r in members(db, project) if r["confirmed_at"]]
        if not confirmed:
            raise HTTPException(409, "Для письма нужен хотя бы один участник с подтверждённой ролью")
        template = require(db, "questionnaire_template", assessment["template_version"])
        sentences = []
        for q in template["questions"]:
            qid = q["id"]
            value = assessment["answers"].get(qid)
            values = value if isinstance(value, list) else [value] if value else []
            if qid == "q7" and value == "no":
                continue
            for choice in values:
                selected = next(o for o in q["options"] if o["value"] == choice)
                sentences.append({"text": template["phrases"][qid][language].format(value=selected["phrase"][language]),
                    "source": {"kind": "answer", "question_id": qid, "value": choice, "template_version": template["version"]}})
            if qid == "q8" and assessment["highlighted_user_ids"]:
                names = ", ".join(r["name"] for r in confirmed if r["user_id"] in assessment["highlighted_user_ids"])
                sentences.append({"text": template["phrases"][qid][language].format(value=names),
                    "source": {"kind": "answer", "question_id": qid, "value": assessment["highlighted_user_ids"], "template_version": template["version"]}})
            comment = assessment["comments"].get(qid)
            if comment:
                sentences.append({"text": comment, "source": {"kind": "comment", "question_id": qid,
                    "value": comment, "template_version": template["version"]}})
        stage = Store.get(db, "stage", stage_key(project))
        stages = [{"name": "prototype", "expected_result": plain(stage["expected_result"]),
            "accepted_at": stage["decided_at"], "version": stage["version"]}] if stage and stage.get("status") == "accepted" and stage.get("decided_at") else []
        previous = [letter for letter in Store.all(db, "recommendation_letter") if letter["project_id"] == project["id"]]
        return {"id": str(uuid4()), "project_id": project["id"], "status": "draft", "language": language,
            "version": max((letter["version"] for letter in previous), default=0) + 1,
            "template_version": template["version"], "assessment_revision": assessment["revision"],
            "body_text": "\n\n".join(s["text"] for s in sentences), "sentences": sentences,
            "members": confirmed, "mode": "template", "ai_used": False,
            "header": {"company_name": project["company_name"], "title": project["title"],
                "started_at": (stage.get("created_at") if stage else None) or project["started_at"], "closed_at": project["closed_at"], "stages": stages,
                "date_note": "Only recorded project/stage dates are shown; timeliness is not inferred."},
            "assessment_snapshot": copy.deepcopy(assessment), "created_at": now().isoformat()}

    @app.get("/api/projects/{id}/letter/preview")
    def preview(id: str, language: Literal["ru", "kk", "en"] = "ru", user=Depends(actor)):
        with store.transaction() as db:
            project = require(db, "project", id)
            owns(db, project, user)
            if project["status"] == "active":
                raise HTTPException(409, "Сначала завершите проект")
            letter = assemble(db, project, language)
            # Stable draft id for the same assessment/language prevents preview refresh spam.
            letter["id"] = "draft-" + hashlib.sha256(json.dumps([id, letter["assessment_revision"], language, letter["version"]]).encode()).hexdigest()[:32]
            Store.put(db, "letter_draft", letter["id"], letter)
            return letter

    def canonical_url(code):
        origin = os.getenv("APP_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")
        parsed = urlsplit(origin)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise HTTPException(503, "Некорректный APP_PUBLIC_URL для QR-кода")
        return origin + "/verify/" + code

    def issue_snapshot(db, project, letter, body, user, replacement=None):
        current = require(db, "project_assessment", project["id"])
        if current["revision"] != letter["assessment_revision"]:
            raise HTTPException(409, "Ответы изменились. Обновите предпросмотр письма")
        if current["answers"]["q6"] == "no":
            raise HTTPException(409, "При ответе «нет» письмо не выдаётся")
        previous = [item for item in Store.all(db, "recommendation_letter") if item["project_id"] == project["id"]]
        if letter["version"] != max((item["version"] for item in previous), default=0) + 1:
            raise HTTPException(409, "Версия письма изменилась. Откройте новый предпросмотр перед выдачей.")
        if not replacement and any(l["project_id"] == project["id"] for l in Store.all(db, "recommendation_letter")):
            raise HTTPException(409, "Письмо уже выдавалось. Используйте перевыпуск")
        issued = copy.deepcopy(letter)
        issued.update(id=str(uuid4()), status="issued", signer_name=body.signer_name,
            signer_position=body.signer_position, issued_at=now().isoformat(), issued_by=user["id"],
            revoked_at=None, replaced_by_id=None)
        copies = []
        for member in issued["members"]:
            cid, code = str(uuid4()), secrets.token_urlsafe(24)
            url = canonical_url(code)
            try:
                pdf = recommendation_pdf(issued, member, url)
            except Exception as exc:
                raise HTTPException(503, "Не удалось сформировать PDF; письмо не выдано. Повторите позже.") from exc
            copies.append({"id": cid, "letter_id": issued["id"], "student_user_id": member["user_id"],
                "name": member["name"], "role": member["role"], "verify_code": code, "verify_url": url,
                "pdf_url": "/api/letter-copies/" + cid + "/pdf", "show_in_portfolio": False,
                "pdf_base64": base64.b64encode(pdf).decode(), "pdf_sha256": hashlib.sha256(pdf).hexdigest()})
        # Every PDF is prepared before any new valid letter or replacement is committed.
        Store.put(db, "recommendation_letter", issued["id"], issued)
        for item in copies:
            Store.put(db, "letter_copy", item["id"], item)
            Store.put(db, "letter_verify", item["verify_code"], {"copy_id": item["id"]})
            notify(db, item["student_user_id"], "letter_issued", issued["id"], {"copy_id": item["id"], "project_id": project["id"]})
        if replacement:
            replacement.update(status="replaced", replaced_by_id=issued["id"], replaced_at=issued["issued_at"])
            Store.put(db, "recommendation_letter", replacement["id"], replacement)
        audit(db, "letter_reissued" if replacement else "letter_issued", user["id"], issued["id"],
            {"project_id": project["id"], "version": issued["version"], "replaces": replacement["id"] if replacement else None})
        return letter_view(db, issued, user)

    @app.post("/api/letters/{lid}/issue", status_code=201)
    def issue(lid: str, body: SignInput, user=Depends(actor)):
        with store.transaction() as db:
            letter = require(db, "letter_draft", lid)
            project = require(db, "project", letter["project_id"])
            owns(db, project, user)
            return issue_snapshot(db, project, letter, body, user)

    @app.post("/api/letters/{lid}/reissue", status_code=201)
    def reissue(lid: str, body: ReissueInput, user=Depends(actor)):
        with store.transaction() as db:
            original = require(db, "recommendation_letter", lid)
            project = require(db, "project", original["project_id"])
            owns(db, project, user)
            if original["status"] not in ("issued", "revoked"):
                raise HTTPException(409, "Письмо уже заменено; откройте последнюю версию")
            draft = require(db, "letter_draft", body.draft_id)
            if draft["project_id"] != project["id"] or draft["language"] != body.language:
                raise HTTPException(409, "Предпросмотр относится к другому проекту или языку")
            return issue_snapshot(db, project, draft, body, user, original)

    @app.post("/api/letters/{lid}/revoke")
    def revoke(lid: str, body: ReasonInput, user=Depends(actor)):
        with store.transaction() as db:
            letter = require(db, "recommendation_letter", lid)
            project = require(db, "project", letter["project_id"])
            owns(db, project, user)
            if letter["status"] == "replaced":
                raise HTTPException(409, "Эта версия уже заменена")
            if letter["status"] != "revoked":
                letter.update(status="revoked", revoked_at=now().isoformat(), revoke_reason=body.reason)
                Store.put(db, "recommendation_letter", lid, letter)
                audit(db, "letter_revoked", user["id"], lid, {"reason": body.reason})
                for item in Store.all(db, "letter_copy"):
                    if item["letter_id"] == lid:
                        notify(db, item["student_user_id"], "letter_revoked", lid, {"copy_id": item["id"]})
            return letter_view(db, letter, user)

    @app.get("/api/me/letter-copies")
    def my_copies(user=Depends(actor)):
        with store.transaction() as db:
            result = []
            for item in Store.all(db, "letter_copy"):
                if item["student_user_id"] == user["id"]:
                    letter = require(db, "recommendation_letter", item["letter_id"])
                    result.append({**copy_view(item), "status": letter["status"], "version": letter["version"],
                        "language": letter["language"], "project_id": letter["project_id"], "title": letter["header"]["title"]})
            return result

    @app.get("/api/users/{id}/portfolio")
    def portfolio(id: str):
        with store.transaction() as db:
            require(db, "user", id)
            result = []
            for item in Store.all(db, "letter_copy"):
                if item["student_user_id"] == id and item["show_in_portfolio"]:
                    letter = require(db, "recommendation_letter", item["letter_id"])
                    result.append({"name": item["name"], "role": item["role"], "verify_url": item["verify_url"],
                        "title": letter["header"]["title"], "status": letter["status"], "version": letter["version"]})
            return result

    def profile_page(title, body, language):
        home = "На главную" if language == "ru" else "Басты бетке"
        nav = "Навигация" if language == "ru" else "Навигация"
        # No private state is embedded in this page; only the explicitly public views below.
        page = ('<!doctype html><html lang="' + language + '"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(title) + ' · Sana Hub</title>'
            '<link rel="stylesheet" href="/static/ui.css"><style>'
            '.public-profile{max-width:840px;margin:auto;padding:24px;min-height:100vh}'
            '.profile-nav{display:flex;gap:16px;align-items:center;flex-wrap:wrap;padding:8px 0 32px}'
            '.profile-nav .brand{font-weight:700;margin-right:auto;text-decoration:none;color:var(--ink)}'
            '.profile-header{margin-bottom:24px}.profile-header h1{font-size:clamp(24px,4vw,36px);line-height:1.25;margin-top:8px}'
            '.profile-list{display:grid;gap:16px}.profile-entry{padding:24px;border:1px solid var(--line);border-radius:var(--r-lg);background:var(--surface);box-shadow:var(--shadow)}'
            '.profile-entry h2{font:600 20px/1.4 var(--f-body);margin-bottom:14px;overflow-wrap:anywhere}'
            '.profile-entry p{margin:8px 0;overflow-wrap:anywhere}.profile-entry .profile-comment{white-space:pre-wrap;border-left:3px solid var(--bright);padding-left:14px;margin-top:16px}'
            '.profile-entry .profile-status{font-size:13px;color:var(--ink-2)}.profile-entry a{display:inline-block;overflow-wrap:anywhere;margin-top:12px}'
            '.profile-empty{padding:28px;border:1px dashed var(--line-strong);border-radius:var(--r-lg);background:var(--surface);color:var(--ink-2)}'
            '.profile-footer{padding-top:28px;color:var(--ink-2);font-size:13px}'
            '@media(max-width:480px){.public-profile{padding:16px}.profile-entry{padding:18px}}'
            '</style></head><body><main class="public-profile"><nav class="profile-nav" aria-label="' + nav + '">'
            '<a class="brand" href="/">SANA HUB</a><a href="/">' + home + '</a>'
            '<a href="?lang=ru" lang="ru" aria-label="Русский">RU</a><a href="?lang=kk" lang="kk" aria-label="Қазақша">ҚАЗ</a></nav>'
            '<header class="profile-header"><p class="eyebrow">Sana Hub</p><h1>' + html.escape(title) + '</h1></header>' + body +
            '<footer class="profile-footer">' + ("Учебные учётные записи Sana Hub. Статус письма проверяется по ссылке."
                if language == "ru" else "Sana Hub оқу тіркелгілері. Хат мәртебесін сілтеме арқылы тексеруге болады.") + '</footer></main></body></html>')
        return HTMLResponse(page, headers={"Cache-Control": "no-store", "Content-Security-Policy": "default-src 'none'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'",
            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})

    @app.get("/profiles/users/{id}", response_class=HTMLResponse)
    def user_profile(id: str, lang: Literal["ru", "kk"] = "ru"):
        entries = portfolio(id)
        title = "Портфолио участника" if lang == "ru" else "Қатысушы портфолиосы"
        statuses = {"issued": {"ru": "Действительно", "kk": "Жарамды"},
            "replaced": {"ru": "Заменено", "kk": "Ауыстырылды"}, "revoked": {"ru": "Отозвано", "kk": "Кері қайтарылды"}}
        blocks = []
        for entry in entries:
            url = entry["verify_url"]
            # Stored URLs originate from APP_PUBLIC_URL. Keep the HTML safe even with imported legacy data.
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                url = "#"
            status = statuses.get(entry["status"], {}).get(lang, entry["status"])
            blocks.append('<article class="profile-entry portfolio-entry"><h2>' + html.escape(entry["title"]) + '</h2>'
                '<p>' + html.escape(entry["name"]) + ' · ' + html.escape(role_label(entry["role"], lang)) + '</p>'
                '<p class="profile-status">' + html.escape(status) + ' · ' + ("Версия " if lang == "ru" else "Нұсқа ") + html.escape(str(entry["version"])) + '</p>'
                '<a href="' + html.escape(url, quote=True) + '" rel="noopener noreferrer">' + ("Проверить письмо" if lang == "ru" else "Хатты тексеру") + '</a></article>')
        body = '<section class="profile-list">' + ''.join(blocks) + '</section>' if blocks else '<p class="profile-empty">' + (
            "Участник пока не опубликовал рекомендательные письма." if lang == "ru" else "Қатысушы ұсыным хаттарын әлі жариялаған жоқ.") + '</p>'
        return profile_page(title, body, lang)

    @app.get("/profiles/teams/{id}", response_class=HTMLResponse)
    def team_profile(id: str, lang: Literal["ru", "kk"] = "ru"):
        entries = public_recommendations(id)
        title = "Отзывы о проектах команды" if lang == "ru" else "Команда жобалары туралы пікірлер"
        q5 = next(q for q in TEMPLATE["questions"] if q["id"] == "q5")
        fates = {choice["value"]: choice["label"][lang] for choice in q5["options"]}
        blocks = []
        for number, entry in enumerate(entries, 1):
            heading = ("Проект " if lang == "ru" else "Жоба ") + str(number)
            fate_label = "Судьба прототипа: " if lang == "ru" else "Прототиптің болашағы: "
            fate = fates.get(entry["prototype_fate"], entry["prototype_fate"])
            comment = '<p class="profile-comment">' + html.escape(entry["result_comment"]) + '</p>' if entry["result_comment"] else ''
            blocks.append('<article class="profile-entry team-review"><h2>' + heading + '</h2><p>' + fate_label + html.escape(fate) + '</p>' + comment + '</article>')
        body = '<section class="profile-list">' + ''.join(blocks) + '</section>' if blocks else '<p class="profile-empty">' + (
            "Команда пока не дала согласие на публикацию отзывов." if lang == "ru" else "Команда пікірлерді жариялауға әлі келісім берген жоқ.") + '</p>'
        return profile_page(title, body, lang)

    @app.patch("/api/letter-copies/{cid}/visibility")
    def visibility(cid: str, body: VisibilityInput, user=Depends(actor)):
        with store.transaction() as db:
            item = require(db, "letter_copy", cid)
            if item["student_user_id"] != user["id"]:
                raise HTTPException(403, "Видимость личной копии меняет только её владелец")
            item["show_in_portfolio"] = body.show_in_portfolio
            Store.put(db, "letter_copy", cid, item)
            audit(db, "letter_copy_visibility", user["id"], cid, body.model_dump())
            return copy_view(item)

    @app.get("/api/letter-copies/{cid}/pdf")
    def pdf_copy(cid: str, user=Depends(actor)):
        with store.transaction() as db:
            item = require(db, "letter_copy", cid)
            letter = require(db, "recommendation_letter", item["letter_id"])
            if item["student_user_id"] != user["id"] and user.get("role") != "moderator":
                owns(db, require(db, "project", letter["project_id"]), user)
            return Response(base64.b64decode(item["pdf_base64"]), media_type="application/pdf",
                headers={"Content-Disposition": 'attachment; filename="sana-recommendation-' + cid + '.pdf"',
                    "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})

    @app.post("/api/letter-copies/{cid}/complaint", status_code=201)
    def complaint(cid: str, body: ComplaintInput, user=Depends(actor)):
        with store.transaction() as db:
            item = require(db, "letter_copy", cid)
            if item["student_user_id"] != user["id"]:
                raise HTTPException(403, "Об ошибке в личной копии сообщает её владелец")
            complaint_id = str(uuid4())
            value = {"id": complaint_id, "copy_id": cid, "author_user_id": user["id"], "text": body.text,
                "status": "new", "created_at": now().isoformat()}
            Store.put(db, "letter_complaint", complaint_id, value)
            audit(db, "letter_complaint_created", user["id"], cid, {"complaint_id": complaint_id})
            for moderator in Store.all(db, "user"):
                if moderator.get("role") == "moderator":
                    notify(db, moderator["id"], "letter_complaint", complaint_id, {"copy_id": cid, "text": body.text})
            return value

    @app.get("/api/letter-complaints")
    def complaints(user=Depends(actor)):
        if user.get("role") != "moderator":
            raise HTTPException(403, "Жалобы на фактические ошибки доступны модератору")
        with store.transaction() as db:
            return sorted(Store.all(db, "letter_complaint"), key=lambda item: (item["created_at"], item["id"]), reverse=True)

    @app.put("/api/projects/{id}/public-consent")
    def consent(id: str, body: ConsentInput, user=Depends(actor)):
        with store.transaction() as db:
            project = require(db, "project", id)
            if not captain(project, user):
                raise HTTPException(403, "Публичное согласие команды указывает капитан")
            project.update(public_consent=body.public_consent, consent_by=user["id"], consent_at=now().isoformat())
            Store.put(db, "project", id, project)
            assessment = Store.get(db, "project_assessment", id)
            if assessment:
                assessment["public_consent"] = body.public_consent
                Store.put(db, "project_assessment", id, assessment)
            audit(db, "project_public_consent", user["id"], id, body.model_dump())
            return project_view(db, project, user)

    @app.get("/api/teams/{id}/project-recommendations")
    def public_recommendations(id: str):
        with store.transaction() as db:
            require(db, "team", id)
            result = []
            for project in Store.all(db, "project"):
                if project["team_id"] == id and project.get("public_consent"):
                    assessment = Store.get(db, "project_assessment", project["id"])
                    if assessment:
                        result.append({"project_id": project["id"], "prototype_fate": assessment["answers"]["q5"],
                            "result_comment": assessment["comments"].get("q1", "")})
            return result

    def verification(db, code):
        lookup = require(db, "letter_verify", code)
        item = require(db, "letter_copy", lookup["copy_id"])
        letter = require(db, "recommendation_letter", item["letter_id"])
        # Knowledge of this unguessable link verifies the named copy regardless of portfolio visibility.
        return {"status": "valid" if letter["status"] == "issued" else letter["status"],
            "letter_id": letter["id"], "version": letter["version"], "language": letter["language"],
            "issued_at": letter["issued_at"], "revoked_at": letter["revoked_at"], "replaced_by_id": letter["replaced_by_id"],
            "recipient_name": item["name"], "recipient_role": item["role"], "company_name": letter["header"]["company_name"],
            "recipient_role_label": role_label(item["role"], letter["language"]),
            "project_title": letter["header"]["title"], "signer_name": letter["signer_name"],
            "signer_position": letter["signer_position"], "pdf_sha256": item["pdf_sha256"], "demo_auth": True}

    @app.get("/api/verify/{code}")
    def verify_json(code: str, response: Response):
        response.headers["Cache-Control"] = "no-store"
        with store.transaction() as db:
            return verification(db, code)

    @app.get("/verify/{code}")
    def verify(code: str, request: Request, format: Literal["html", "json"] = "html"):
        with store.transaction() as db:
            value = verification(db, code)
        if format == "json" or "application/json" in request.headers.get("accept", ""):
            from fastapi.responses import JSONResponse
            return JSONResponse(value, headers={"Cache-Control": "no-store"})
        status = {"valid": "Действительно / Жарамды / Valid", "replaced": "Заменено / Ауыстырылды / Replaced", "revoked": "Отозвано / Кері қайтарылды / Revoked"}[value["status"]]
        fields = [("Участник / Қатысушы", value["recipient_name"]), ("Роль / Рөлі", value["recipient_role_label"]),
            ("Проект / Жоба", value["project_title"]), ("Компания", value["company_name"]),
            ("Подписант / Қол қоюшы", value["signer_name"] + ", " + value["signer_position"]),
            ("Выдано / Берілген күні", value["issued_at"][:10]), ("Версия / Нұсқа", str(value["version"]))]
        markup = ''.join('<dt>' + html.escape(label) + '</dt><dd>' + html.escape(text) + '</dd>' for label, text in fields)
        page = '<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sana Hub · Проверка письма</title><style>body{font:17px/1.6 system-ui;margin:5vh auto;padding:24px;max-width:700px;background:#f4f8f5;color:#16392c}article{background:white;padding:32px;border-radius:20px}h1{font-size:28px}dt{color:#526a60}dd{margin:0 0 14px;overflow-wrap:anywhere}small{display:block;color:#526a60}</style><article><p>SANA HUB</p><h1>' + status + '</h1><dl>' + markup + '</dl><small>Роли указаны командой и подтверждены участниками. Демонстрационные учётные записи; это не электронная подпись.</small><small>Рөлдерді команда көрсетті, қатысушылар растады. Демонстрациялық тіркелгілер; бұл электрондық қолтаңба емес.</small></article></html>'
        return HTMLResponse(page, headers={"Cache-Control": "no-store", "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})
