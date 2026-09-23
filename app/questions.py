"""Public Q&A with transactional limits, private moderation and explicit provenance.

The injected actor dependency must resolve a server-side identity. Client supplied
demo role headers alone are not authentication and are not consulted here.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Literal
from uuid import uuid4

from fastapi import Depends, HTTPException, Query
from pydantic import Field, field_validator

from app.rating import edit_card
from app.schemas import CardContent, CardField, Model, TaskCard
from app.store import Store


def utcnow():
    return datetime.now(timezone.utc)


class _TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.blocked = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "iframe", "object"}:
            self.blocked.append(tag)
        elif not self.blocked and tag in {"br", "p", "div", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.blocked:
            # Nested markup inside a script is still discarded.
            self.blocked = self.blocked[:self.blocked.index(tag)]
        elif not self.blocked and tag in {"p", "div", "li"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.blocked:
            self.parts.append(data)


def clean_text(value):
    """Sanitize before measuring lengths; never render customer text as HTML."""
    if not isinstance(value, str):
        raise ValueError("Ожидается текст")
    if len(value) > 30000:
        raise ValueError("Слишком длинный текст")
    decoded = value
    for _ in range(8):
        unescaped = html.unescape(decoded)
        if unescaped == decoded:
            break
        decoded = unescaped
    else:
        raise ValueError("Слишком много вложенных HTML-сущностей")
    parser = _TextOnly()
    parser.feed(decoded)
    parser.close()
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ud800-\udfff]", "", "".join(parser.parts)).strip()


class QuestionInput(Model):
    text: str = Field(min_length=10, max_length=1000)
    _clean = field_validator("text", mode="before")(clean_text)


class QuestionEditInput(QuestionInput):
    version: int = Field(ge=1)


class AnswerInput(Model):
    text: str = Field(min_length=1, max_length=3000)
    _clean = field_validator("text", mode="before")(clean_text)


class AnswerEditInput(AnswerInput):
    version: int = Field(ge=1)


class ReasonInput(Model):
    reason: str = Field(min_length=1, max_length=1000)
    version: int | None = Field(default=None, ge=1)
    _clean = field_validator("reason", mode="before")(clean_text)


class MergeInput(Model):
    duplicate_of_id: str = Field(min_length=1, max_length=200)
    version: int | None = Field(default=None, ge=1)


class SubscriptionInput(Model):
    subscribed: bool


class ApplyFieldInput(Model):
    field: CardField
    text: str = Field(min_length=1, max_length=3000)
    card_revision: int = Field(ge=1)
    answer_version: int = Field(ge=1)
    _clean = field_validator("text", mode="before")(clean_text)


def register_questions(app, store, require, actor, owner, audit, notify, suggest_field=None):
    """Install routes; all collaborators use the current SQLite transaction.

    Optional suggest_field(question, answer, card_record) runs outside the lock
    and returns {field,text,mode,provider?}. Its output remains unconfirmed.
    """
    def published(db, card_id):
        card = require(db, "card", card_id)
        if not card.get("snapshot"):
            raise HTTPException(409, "Вопросы доступны только в опубликованной карточке")
        return card

    def student(user):
        if user.get("role") not in {"student", "team"} or not user.get("id"):
            raise HTTPException(403, "Задать вопрос может только студент")

    def owns(db, card, user):
        if user.get("role") != "business":
            return False
        try:
            owner(db, card, user)
            return True
        except HTTPException as exc:
            if exc.status_code in {403, 404}:
                return False
            raise

    def visible(question, user):
        if question["status"] == "hidden":
            return user.get("id") == question["author_user_id"] or user.get("role") == "moderator"
        if question["status"] == "declined":
            return user.get("id") == question["author_user_id"]
        return True

    def load(db, qid, user):
        question = require(db, "card_question", qid)
        if not visible(question, user):
            raise HTTPException(404, "Вопрос не найден")
        card = published(db, question["card_id"])
        return question, card

    def check_version(record, version):
        if version is not None and record["version"] != version:
            raise HTTPException(409, "Вопрос или ответ изменился. Обновите данные перед действием")

    def require_new(question):
        if question["status"] != "new":
            raise HTTPException(409, "Это действие доступно только для вопроса без решения")

    def subscription_key(card_id, user_id):
        return json.dumps([card_id, user_id], ensure_ascii=False)

    def view(db, question, user, card=None):
        card = card or require(db, "card", question["card_id"])
        can_manage = owns(db, card, user)
        answer = Store.get(db, "card_answer", question["id"])
        if answer:
            answer = dict(answer)
            if can_manage or user.get("role") == "moderator":
                answer["revisions"] = sorted(
                    [r for r in Store.all(db, "card_answer_revision") if r["answer_id"] == answer["id"]],
                    key=lambda r: r["version"])
        result = {k: v for k, v in question.items() if k not in {"decline_reason", "hide_reason"}}
        if question["status"] == "declined" and user.get("id") == question["author_user_id"]:
            result["decline_reason"] = question["decline_reason"]
        if question["status"] == "hidden" and visible(question, user):
            result["hide_reason"] = question["hide_reason"]
        if result.get("duplicate_of_id"):
            target = Store.get(db, "card_question", result["duplicate_of_id"])
            if not target or not visible(target, user):
                result.update(duplicate_of_id=None, duplicate_unavailable=True)
        result.update(answer=answer,
            can_edit=user.get("id") == question["author_user_id"] and question["status"] == "new" and not answer,
            can_answer=can_manage and question["status"] == "new" and not answer,
            can_manage=can_manage and question["status"] in {"new", "answered"},
            can_hide=user.get("role") == "moderator" and question["status"] != "hidden")
        return result

    def today_count(db, card_id, user_id):
        # A calendar day is UTC for all clients, documented by the list response.
        day = utcnow().date().isoformat()
        return sum(q["card_id"] == card_id and q["author_user_id"] == user_id
                   and q["created_at"][:10] == day for q in Store.all(db, "card_question"))

    def save_question(db, question):
        question["version"] += 1
        question["updated_at"] = utcnow().isoformat()
        Store.put(db, "card_question", question["id"], question)

    def owner_recipients(db, card):
        company = card.get("company_id", "demo-company")
        return {u["id"] for u in Store.all(db, "user")
                if u.get("role") == "business" and u.get("company_id") == company}

    @app.get("/api/cards/{id}/questions")
    def list_questions(id: str, filter: Literal["all", "answered", "unanswered"] = "all",
                       limit: int = Query(default=100, ge=1, le=200), offset: int = Query(default=0, ge=0),
                       user: dict = Depends(actor)):
        with store.transaction() as db:
            card = published(db, id)
            items = [q for q in Store.all(db, "card_question") if q["card_id"] == id and visible(q, user)]
            unanswered = sum(q["status"] == "new" for q in items)
            total = len(items)
            if filter == "answered":
                items = [q for q in items if q["status"] == "answered"]
            elif filter == "unanswered":
                items = [q for q in items if q["status"] == "new"]
            items.sort(key=lambda q: (q["created_at"], q["id"]), reverse=True)
            sub = Store.get(db, "card_subscription", subscription_key(id, user.get("id")))
            remaining = max(0, 5 - today_count(db, id, user.get("id")))
            return {"items": [view(db, q, user, card) for q in items[offset:offset + limit]],
                    "total": total, "filtered_count": len(items), "unanswered_count": unanswered,
                    "subscribed": bool(sub and sub["subscribed"]), "remaining_today": remaining,
                    "can_ask": user.get("role") in {"student", "team"} and remaining > 0,
                    "limit_timezone": "UTC"}

    @app.get("/api/cards/{id}/questions/similar")
    def similar_questions(id: str, q: str = Query(min_length=1, max_length=1000), user: dict = Depends(actor)):
        stopwords = {"какие", "какой", "какая", "будет", "можно", "нужно", "этого", "для", "как", "что", "или", "при", "the", "and"}
        tokens = {v for v in re.findall(r"\w+", clean_text(q).casefold()) if len(v) > 2 and v not in stopwords}
        with store.transaction() as db:
            card = published(db, id)
            matches = []
            for question in Store.all(db, "card_question"):
                if question["card_id"] != id or not visible(question, user):
                    continue
                answer = Store.get(db, "card_answer", question["id"])
                words = set(re.findall(r"\w+", (question["text"] + " " + (answer or {}).get("text", "")).casefold()))
                shared = tokens & words
                if shared:
                    matches.append((len(shared) / max(1, len(tokens)), question))
            matches.sort(key=lambda pair: (-pair[0], pair[1]["created_at"], pair[1]["id"]))
            return {"items": [{**view(db, question, user, card), "similarity": score}
                              for score, question in matches[:5]], "method": "lexical"}

    @app.post("/api/cards/{id}/questions", status_code=201)
    def create_question(id: str, body: QuestionInput, user: dict = Depends(actor)):
        student(user)
        with store.transaction() as db:
            card = published(db, id)
            if today_count(db, id, user["id"]) >= 5:
                raise HTTPException(429, "Не больше пяти вопросов на карточку в сутки (UTC)")
            now = utcnow().isoformat()
            question = {"id": str(uuid4()), "card_id": id, "author_user_id": user["id"],
                "author_name": user.get("name", user["id"]), "team_id": user.get("team_id"),
                "text": body.text, "status": "new", "duplicate_of_id": None,
                "created_at": now, "updated_at": now, "version": 1}
            Store.put(db, "card_question", question["id"], question)
            audit(db, "question.created", user["id"], question["id"], {"card_id": id})
            for recipient in owner_recipients(db, card):
                notify(db, recipient, "new_question", question["id"], {"card_id": id, "created_at": now})
            return view(db, question, user, card)

    @app.get("/api/questions/{qid}")
    def get_question(qid: str, user: dict = Depends(actor)):
        with store.transaction() as db:
            question, card = load(db, qid, user)
            return view(db, question, user, card)

    @app.patch("/api/questions/{qid}")
    def edit_question(qid: str, body: QuestionEditInput, user: dict = Depends(actor)):
        student(user)
        with store.transaction() as db:
            question, card = load(db, qid, user)
            if question["author_user_id"] != user["id"]:
                raise HTTPException(403, "Редактировать вопрос может только его автор")
            require_new(question)
            check_version(question, body.version)
            if Store.get(db, "card_answer", qid):
                raise HTTPException(409, "После ответа вопрос не редактируется")
            old_text = question["text"]
            question["text"] = body.text
            save_question(db, question)
            audit(db, "question.edited", user["id"], qid, {"previous_text": old_text})
            return view(db, question, user, card)

    @app.post("/api/questions/{qid}/answer", status_code=201)
    def create_answer(qid: str, body: AnswerInput, user: dict = Depends(actor)):
        with store.transaction() as db:
            question, card = load(db, qid, user)
            owner(db, card, user)
            require_new(question)
            if Store.get(db, "card_answer", qid):
                raise HTTPException(409, "Ответ уже существует; используйте редактирование")
            now = utcnow().isoformat()
            answer = {"id": str(uuid4()), "question_id": qid, "author_user_id": user["id"],
                "text": body.text, "is_edited": False, "source_for_field": None,
                "created_at": now, "updated_at": now, "version": 1}
            Store.put(db, "card_answer", qid, answer)
            question["status"] = "answered"
            save_question(db, question)
            audit(db, "answer.created", user["id"], answer["id"], {"question_id": qid})
            recipients = {question["author_user_id"]} | {s["user_id"] for s in Store.all(db, "card_subscription")
                if s["card_id"] == question["card_id"] and s["subscribed"]}
            for recipient in recipients:
                notify(db, recipient, "question_answered", qid, {"card_id": question["card_id"], "answer_id": answer["id"]})
            return view(db, question, user, card)

    @app.patch("/api/questions/{qid}/answer")
    def edit_answer(qid: str, body: AnswerEditInput, user: dict = Depends(actor)):
        with store.transaction() as db:
            question, card = load(db, qid, user)
            owner(db, card, user)
            if question["status"] != "answered":
                raise HTTPException(409, "Этот ответ нельзя редактировать")
            answer = require(db, "card_answer", qid)
            check_version(answer, body.version)
            if answer["text"] != body.text:
                revision = {"id": str(uuid4()), "answer_id": answer["id"], "text": answer["text"],
                    "version": answer["version"], "edited_at": utcnow().isoformat(), "edited_by": user["id"]}
                Store.put(db, "card_answer_revision", revision["id"], revision)
                answer.update(text=body.text, is_edited=True, version=answer["version"] + 1,
                              updated_at=revision["edited_at"])
                Store.put(db, "card_answer", qid, answer)
                save_question(db, question)
                audit(db, "answer.edited", user["id"], answer["id"], {"revision_id": revision["id"]})
            return view(db, question, user, card)

    @app.post("/api/questions/{qid}/decline")
    def decline(qid: str, body: ReasonInput, user: dict = Depends(actor)):
        with store.transaction() as db:
            question, card = load(db, qid, user)
            owner(db, card, user)
            require_new(question)
            check_version(question, body.version)
            question.update(status="declined", decline_reason=body.reason)
            save_question(db, question)
            audit(db, "question.declined", user["id"], qid, {"reason": body.reason})
            notify(db, question["author_user_id"], "question_declined", qid, {"card_id": question["card_id"]})
            # The action confirmation does not leak a now-private question.
            return {"id": qid, "status": "declined", "version": question["version"]}

    @app.post("/api/questions/{qid}/merge")
    def merge(qid: str, body: MergeInput, user: dict = Depends(actor)):
        with store.transaction() as db:
            question, card = load(db, qid, user)
            owner(db, card, user)
            require_new(question)
            check_version(question, body.version)
            target, _ = load(db, body.duplicate_of_id, user)
            if target["id"] == qid or target["card_id"] != question["card_id"] or target["status"] not in {"new", "answered"}:
                raise HTTPException(422, "Выберите исходный публичный вопрос этой карточки")
            # Canonical targets cannot themselves become duplicates, avoiding chains.
            if any(q.get("duplicate_of_id") == qid for q in Store.all(db, "card_question")):
                raise HTTPException(409, "На этот исходный вопрос уже ссылаются другие вопросы")
            question.update(status="duplicate", duplicate_of_id=target["id"])
            save_question(db, question)
            audit(db, "question.merged", user["id"], qid, {"duplicate_of_id": target["id"]})
            return view(db, question, user, card)

    @app.post("/api/questions/{qid}/hide")
    def hide(qid: str, body: ReasonInput, user: dict = Depends(actor)):
        if user.get("role") != "moderator":
            raise HTTPException(403, "Скрыть вопрос может только модератор")
        with store.transaction() as db:
            question, card = load(db, qid, user)
            check_version(question, body.version)
            if question["status"] != "hidden":
                question.update(status="hidden", hide_reason=body.reason)
                save_question(db, question)
                audit(db, "question.hidden", user["id"], qid, {"reason": body.reason})
            return view(db, question, user, card)

    @app.post("/api/cards/{id}/subscribe")
    def subscribe(id: str, body: SubscriptionInput, user: dict = Depends(actor)):
        student(user)
        with store.transaction() as db:
            published(db, id)
            key = subscription_key(id, user["id"])
            Store.put(db, "card_subscription", key, {"id": key, "card_id": id, "user_id": user["id"],
                "subscribed": body.subscribed, "updated_at": utcnow().isoformat()})
            return {"subscribed": body.subscribed}

    @app.post("/api/questions/{qid}/suggest-field")
    def suggest(qid: str, user: dict = Depends(actor)):
        with store.transaction() as db:
            question, card = load(db, qid, user)
            owner(db, card, user)
            if question["status"] != "answered":
                raise HTTPException(409, "Сначала ответьте на вопрос")
            answer = require(db, "card_answer", qid)
        if suggest_field:
            result = suggest_field(question, answer, card)
        else:
            rules = [("data", ("данн", "материал", "dataset")), ("constraints", ("срок", "огранич", "deadline")),
                     ("success_criteria", ("провер", "приём", "критер", "прием")), ("users", ("пользоват", "аудитор")),
                     ("contact", ("контакт", "связат")), ("expected_result", ("результат", "прототип"))]
            field = next((field for field, words in rules if any(w in question["text"].casefold() for w in words)), "context")
            result = {"field": field, "text": answer["text"], "mode": "mock", "provider": "deterministic-template"}
        # External suggestion output is data, not authority to write a field.
        if not isinstance(result, dict) or result.get("field") not in CardContent.model_fields:
            raise HTTPException(502, "Некорректное предложение поля")
        try:
            value = AnswerInput(text=result.get("text"))
        except ValueError as exc:
            raise HTTPException(502, "Некорректный текст предложения") from exc
        if value.text != answer["text"]:
            raise HTTPException(502, "Предложение должно сохранять дословный текст ответа")
        if result.get("mode") not in {"mock", "live", "partial"}:
            raise HTTPException(502, "Не указан режим предложения")
        with store.transaction() as db:
            current, latest = load(db, qid, user)
            owner(db, latest, user)
            if current["status"] != "answered" or latest["revision"] != card["revision"]:
                raise HTTPException(409, "Карточка или вопрос изменились. Запросите предложение снова")
            check_version(require(db, "card_answer", qid), answer["version"])
        return {"field": result["field"], "text": value.text, "mode": result["mode"],
                "provider": result.get("provider", "unknown"), "card_revision": card["revision"],
                "answer_version": answer["version"], "requires_confirmation": True}

    @app.post("/api/questions/{qid}/apply-field")
    def apply_field(qid: str, body: ApplyFieldInput, user: dict = Depends(actor)):
        with store.transaction() as db:
            question, card = load(db, qid, user)
            owner(db, card, user)
            if question["status"] != "answered":
                raise HTTPException(409, "Перенести можно только опубликованный ответ")
            if card["revision"] != body.card_revision:
                raise HTTPException(409, "Карточка изменилась. Загрузите актуальную версию")
            answer = require(db, "card_answer", qid)
            check_version(answer, body.answer_version)
            updated = edit_card(TaskCard.model_validate(card["card"]), {body.field: body.text})
            updated.confirmations.pop(body.field, None)  # Even equal text requires explicit reconfirmation.
            if sum(len(getattr(updated, f)) for f in CardContent.model_fields) > 30000:
                raise HTTPException(422, "Слишком длинная карточка")
            card["card"] = updated.model_dump()
            card["revision"] += 1
            reference = f"answer:{answer['id']}:{answer['version']}"
            if body.text == answer["text"]:
                evidence = {"source_id": reference, "quote": body.text}
            else:
                evidence = {"source_id": f"manual:{question['card_id']}:{card['revision']}:{body.field}",
                            "quote": body.text, "based_on_source_id": reference}
            card.setdefault("evidence", {})[body.field] = evidence
            if card.get("specification", {}).get("content"):
                card["specification"].update(status="stale", approved_at=None)
            answer["source_for_field"] = body.field
            Store.put(db, "card_answer", qid, answer)
            Store.put(db, "card", question["card_id"], card)
            audit(db, "answer.applied_to_card", user["id"], answer["id"],
                  {"field": body.field, "card_id": question["card_id"], "card_revision": card["revision"],
                   "answer_version": answer["version"]})
            return {"card_id": question["card_id"], "revision": card["revision"], "field": body.field,
                    "requires_confirmation": True}
