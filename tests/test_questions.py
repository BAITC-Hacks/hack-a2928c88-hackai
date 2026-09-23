"""Q&A acceptance tests exercise real sessions, ownership and SQLite transactions."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.community import register_community, seed_community
from app.questions import clean_text, register_questions
from app.rating import confirm_fields
from app.schemas import TaskCard
from app.store import Store


HEADERS = {"X-Community-Request": "1"}
STUDENT = "team-one:captain"
OTHER_STUDENT = "team-two:captain"
OWNER = "demo-business"
OUTSIDER = "other-business"
MODERATOR = "demo-moderator"


class Harness:
    def __init__(self, path, suggester=None):
        self.store = Store(path)
        self.app = FastAPI()
        with self.store.transaction() as db:
            for id in ["team-one", "team-two"]:
                Store.put(db, "team", id, {"id": id, "name": id})
            for id in ["published", "other-card", "draft"]:
                card = confirm_fields(TaskCard(id=id, draft_id="source", industry="Education", title="Задача",
                    data="Исходные данные подтверждены"), ["title", "data"], business_actor=OWNER)
                snapshot = {**card.model_dump(), "revision": 1}
                Store.put(db, "card", id, {"card": card.model_dump(), "snapshot": snapshot if id != "draft" else None,
                    "revision": 1, "evidence": {}, "specification": {"content": {"title": "ТЗ"}, "status": "approved", "approved_at": "2026-09-23"}})
        seed_community(self.store)

        def require(db, kind, id):
            value = Store.get(db, kind, id)
            if value is None:
                raise HTTPException(404, "Не найдено")
            return value

        helpers = register_community(self.app, self.store, require)
        register_questions(self.app, self.store, require, **helpers, suggest_field=suggester)
        self.client = TestClient(self.app)

    def call(self, method, path, user=STUDENT, body=None):
        if user is not None:
            logged_in = self.client.post("/api/community/session", headers=HEADERS, json={"user_id": user})
            assert logged_in.status_code == 200
        return self.client.request(method, path, headers=HEADERS, json=body)

    def create(self, text="Какие данные доступны студентам?", user=STUDENT, card="published"):
        response = self.call("POST", f"/api/cards/{card}/questions", user, {"text": text})
        assert response.status_code == 201, response.text
        return response.json()

    def answer(self, question, text="Доступна обезличенная таблица из ста строк."):
        response = self.call("POST", f"/api/questions/{question['id']}/answer", OWNER, {"text": text})
        assert response.status_code == 201, response.text
        return response.json()

    def listed(self, user=STUDENT, query=""):
        response = self.call("GET", "/api/cards/published/questions" + query, user)
        assert response.status_code == 200, response.text
        return response.json()

    def records(self, kind):
        with self.store.transaction() as db:
            return Store.all(db, kind)


@pytest.fixture
def factory(tmp_path, monkeypatch):
    monkeypatch.setenv("COMMUNITY_DEMO", "1")
    instances = []

    def build(suggester=None):
        harness = Harness(tmp_path / f"{uuid4()}.db", suggester)
        instances.append(harness)
        return harness

    yield build
    for instance in instances:
        instance.client.close()


@pytest.fixture
def qa(factory):
    return factory()


def test_real_session_required_and_role_header_cannot_impersonate(qa):
    assert qa.client.get("/api/cards/published/questions", headers={"X-Demo-Role": "business"}).status_code == 401
    assert qa.client.post("/api/community/session", json={"user_id": OWNER}).status_code == 403
    qa.call("GET", "/api/cards/published/questions")
    assert qa.client.post("/api/cards/published/questions", json={"text": "Вопрос с поддельным заголовком"}).status_code == 403
    assert qa.call("POST", "/api/cards/published/questions", OWNER, {"text": "Вопрос от бизнеса запрещён"}).status_code == 403
    assert qa.call("POST", "/api/cards/published/questions", STUDENT,
                   {"text": "Можно ли подменить автора?", "author_user_id": OTHER_STUDENT}).status_code == 422


def test_question_publication_text_limits_and_sanitization(qa):
    assert qa.call("POST", "/api/cards/draft/questions", body={"text": "Нельзя спрашивать до публикации"}).status_code == 409
    for text in [" " * 10, "a" * 9, "a" * 1001, "<script>12345678901234567890</script>"]:
        assert qa.call("POST", "/api/cards/published/questions", body={"text": text}).status_code == 422
    for text in ["a" * 10, "a" * 1000]:
        assert qa.create(text)["text"] == text
    value = qa.create("<b>Какие данные</b> доступны? <script>alert(1)</script>")
    assert value["text"] == "Какие данные доступны?"
    assert value["author_user_id"] == STUDENT and value["team_id"] == "team-one"
    assert value["can_edit"] is True and value["can_answer"] is False
    assert clean_text("&lt;b&gt;Алматы&lt;/b&gt;: 2 < 3 и 5 > 4") == "Алматы: 2 < 3 и 5 > 4"
    assert clean_text("&amp;lt;script&amp;gt;alert(1)&amp;lt;/script&amp;gt;Данные доступны") == "Данные доступны"


def test_daily_limit_counts_terminal_questions_and_resets_at_utc_day(qa, monkeypatch):
    current = datetime(2026, 9, 23, 23, 59, tzinfo=timezone.utc)
    monkeypatch.setattr("app.questions.utcnow", lambda: current)
    items = [qa.create(f"Вопрос про данные номер {i}") for i in range(5)]
    qa.call("POST", f"/api/questions/{items[0]['id']}/decline", OWNER, {"reason": "Не по теме"})
    assert qa.call("POST", "/api/cards/published/questions", body={"text": "Шестой вопрос не пройдёт"}).status_code == 429
    assert qa.listed()["remaining_today"] == 0
    qa.create(user=OTHER_STUDENT)
    current += timedelta(minutes=2)
    assert qa.listed()["remaining_today"] == 5
    qa.create()


def test_six_concurrent_creations_cannot_bypass_daily_limit(qa):
    clients = [TestClient(qa.app) for _ in range(6)]
    try:
        for client in clients:
            assert client.post("/api/community/session", headers=HEADERS, json={"user_id": STUDENT}).status_code == 200
        def create(client):
            return client.post("/api/cards/published/questions", headers=HEADERS,
                               json={"text": "Одновременный вопрос о данных"}).status_code
        with ThreadPoolExecutor(max_workers=6) as executor:
            codes = list(executor.map(create, clients))
        assert sorted(codes) == [201, 201, 201, 201, 201, 429]
        assert len(qa.records("card_question")) == 5
    finally:
        for client in clients:
            client.close()


def test_author_can_edit_only_unanswered_current_version(qa):
    question = qa.create()
    path = f"/api/questions/{question['id']}"
    assert qa.call("PATCH", path, OTHER_STUDENT, {"text": "Чужая правка запрещена", "version": 1}).status_code == 403
    edited = qa.call("PATCH", path, body={"text": "Какие материалы дадут команде?", "version": 1}).json()
    assert edited["version"] == 2
    assert qa.call("PATCH", path, body={"text": "Устаревшая правка запрещена", "version": 1}).status_code == 409
    qa.answer(edited)
    assert qa.call("PATCH", path, body={"text": "Правка после ответа запрещена", "version": 3}).status_code == 409


def test_owner_only_single_answer_and_revision_history(qa):
    question = qa.create()
    path = f"/api/questions/{question['id']}/answer"
    for actor in [STUDENT, OUTSIDER, MODERATOR]:
        assert qa.call("POST", path, actor, {"text": "Чужой ответ"}).status_code == 403
    for text in [" ", "a" * 3001]:
        assert qa.call("POST", path, OWNER, {"text": text}).status_code == 422
    first = qa.answer(question, "Первый официальный ответ")
    assert qa.call("POST", path, OWNER, {"text": "Второй ответ"}).status_code == 409
    assert qa.listed(OTHER_STUDENT)["items"][0]["answer"]["text"] == "Первый официальный ответ"
    changed = qa.call("PATCH", path, OWNER, {"text": "Исправленный ответ", "version": 1}).json()
    assert changed["answer"]["is_edited"] and changed["answer"]["version"] == 2
    assert changed["answer"]["revisions"][0]["text"] == first["answer"]["text"]
    assert "revisions" not in qa.listed(OTHER_STUDENT)["items"][0]["answer"]
    assert qa.call("PATCH", path, OWNER, {"text": "Конфликтует", "version": 1}).status_code == 409
    repeated = qa.call("PATCH", path, OWNER, {"text": "Исправленный ответ", "version": 2}).json()
    assert repeated["answer"]["version"] == 2 and len(qa.records("card_answer_revision")) == 1


def test_private_decline_hidden_question_and_similar_search(qa):
    declined = qa.create("Материалы для конфиденциального проекта?")
    hidden = qa.create("Материалы для скрытого проекта?")
    normal = qa.create("Материалы для обычного проекта?")
    qa.call("POST", f"/api/questions/{declined['id']}/decline", OWNER, {"reason": "<b>Причина видна автору</b>"})
    assert qa.call("POST", f"/api/questions/{hidden['id']}/hide", OWNER, {"reason": "Не модератор"}).status_code == 403
    qa.call("POST", f"/api/questions/{hidden['id']}/hide", MODERATOR, {"reason": "Нарушение правил"})
    own = qa.listed()["items"]
    assert len(own) == 3
    assert next(q for q in own if q["id"] == declined["id"])["decline_reason"] == "Причина видна автору"
    assert len(qa.listed(OTHER_STUDENT)["items"]) == 1
    assert len(qa.listed(OWNER)["items"]) == 1
    assert len(qa.listed(MODERATOR)["items"]) == 2
    result = qa.call("GET", "/api/cards/published/questions/similar?q=Материалы", OTHER_STUDENT).json()
    assert [q["id"] for q in result["items"]] == [normal["id"]]
    assert qa.call("POST", f"/api/questions/{hidden['id']}/answer", OWNER, {"text": "Не прочитать скрытый"}).status_code == 404
    assert qa.call("PATCH", f"/api/questions/{declined['id']}", body={"text": "Не вернуть в новые правкой", "version": 2}).status_code == 409


def test_filters_are_server_side_and_counts_reflect_visible_questions(qa):
    answered = qa.create()
    qa.answer(answered)
    second = qa.create("Что передать в результате проекта?")
    assert qa.listed(query="?filter=answered")["items"][0]["id"] == answered["id"]
    unans = qa.listed(query="?filter=unanswered")
    assert unans["total"] == 2 and unans["filtered_count"] == 1 and unans["unanswered_count"] == 1
    assert unans["items"][0]["id"] == second["id"]
    assert qa.call("GET", "/api/cards/published/questions?filter=hidden").status_code == 422


def test_single_question_link_respects_privacy_and_works_outside_current_page(qa):
    question = qa.create("Исходный вопрос для ссылки дубликата")
    second = qa.create("Ещё один вопрос занимает первую страницу")
    path = f"/api/questions/{question['id']}"
    public = qa.call("GET", path, OTHER_STUDENT)
    assert public.status_code == 200 and public.json()["id"] == question["id"]
    assert qa.call("GET", "/api/questions/not-found", OTHER_STUDENT).status_code == 404
    qa.call("POST", path + "/hide", MODERATOR, {"reason": "Нарушение правил"})
    assert qa.call("GET", path, OTHER_STUDENT).status_code == 404
    assert qa.call("GET", path, OWNER).status_code == 404
    assert qa.call("GET", path, STUDENT).json()["hide_reason"] == "Нарушение правил"
    assert qa.call("GET", path, MODERATOR).status_code == 200
    declined = f"/api/questions/{second['id']}"
    qa.call("POST", declined + "/decline", OWNER, {"reason": "Личная причина"})
    assert qa.call("GET", declined, OTHER_STUDENT).status_code == 404
    assert qa.call("GET", declined, MODERATOR).status_code == 404
    assert qa.call("GET", declined, STUDENT).json()["decline_reason"] == "Личная причина"


def test_duplicate_targets_must_be_same_card_canonical_and_visible(qa):
    original = qa.create()
    duplicate = qa.create("Какие данные доступны другой команде?")
    cross_card = qa.create(card="other-card")
    path = f"/api/questions/{duplicate['id']}/merge"
    assert qa.call("POST", path, OWNER, {"duplicate_of_id": cross_card["id"]}).status_code == 422
    assert qa.call("POST", path, OWNER, {"duplicate_of_id": duplicate["id"]}).status_code == 422
    assert qa.call("POST", path, OUTSIDER, {"duplicate_of_id": original["id"]}).status_code == 403
    result = qa.call("POST", path, OWNER, {"duplicate_of_id": original["id"], "version": 1}).json()
    assert result["status"] == "duplicate" and result["duplicate_of_id"] == original["id"]
    third = qa.create("Вопрос для проверки циклов ссылок")
    assert qa.call("POST", f"/api/questions/{original['id']}/merge", OWNER, {"duplicate_of_id": third["id"]}).status_code == 409
    assert qa.call("POST", f"/api/questions/{third['id']}/merge", OWNER, {"duplicate_of_id": duplicate["id"]}).status_code == 422
    qa.call("POST", f"/api/questions/{original['id']}/hide", MODERATOR, {"reason": "Скрыт модератором"})
    public_duplicate = next(q for q in qa.listed(OTHER_STUDENT)["items"] if q["id"] == duplicate["id"])
    assert public_duplicate["duplicate_of_id"] is None and public_duplicate["duplicate_unavailable"]


def test_notifications_go_only_to_owner_author_and_active_subscribers(qa):
    assert qa.call("POST", "/api/cards/published/subscribe", OTHER_STUDENT, {"subscribed": True}).status_code == 200
    qa.call("POST", "/api/cards/published/subscribe", STUDENT, {"subscribed": True})
    assert qa.listed()["subscribed"]
    question = qa.create()
    outbox = qa.records("community_outbox")
    assert [(n["recipient_id"], n["kind"]) for n in outbox] == [(OWNER, "new_question")]
    assert outbox[0]["due_at"] > outbox[0]["created_at"]
    qa.answer(question)
    replies = [n for n in qa.records("community_outbox") if n["kind"] == "question_answered"]
    assert {n["recipient_id"] for n in replies} == {STUDENT, OTHER_STUDENT} and len(replies) == 2
    qa.call("POST", "/api/cards/published/subscribe", OTHER_STUDENT, {"subscribed": False})
    next_question = qa.create("Ещё один вопрос после отписки")
    qa.answer(next_question)
    assert len([n for n in qa.records("community_outbox") if n["kind"] == "question_answered"]) == 3
    events = {e["event"] for e in qa.records("community_audit")}
    assert {"question.created", "answer.created"} <= events


def test_transfer_requires_owner_and_fresh_card_and_answer(qa):
    from app.review import review_view
    with qa.store.transaction() as db:
        reviewed = Store.get(db, 'card', 'published')
        for key in ('review', 'nvidia_review'):
            reviewed[key] = {'status': 'complete', 'revision': 1, 'issues': []}
        Store.put(db, 'card', 'published', reviewed)
    question = qa.create()
    answered = qa.answer(question)
    base = f"/api/questions/{question['id']}"
    assert qa.call("POST", base + "/suggest-field", OUTSIDER).status_code == 403
    suggestion = qa.call("POST", base + "/suggest-field", OWNER).json()
    assert suggestion["mode"] == "mock" and suggestion["field"] == "data"
    assert suggestion["text"] == answered["answer"]["text"]
    body = {key: suggestion[key] for key in ["field", "text", "card_revision", "answer_version"]}
    assert qa.call("POST", base + "/apply-field", OWNER, {**body, "card_revision": 2}).status_code == 409
    assert qa.call("POST", base + "/apply-field", OWNER, {**body, "answer_version": 2}).status_code == 409
    assert qa.call("POST", base + "/apply-field", STUDENT, body).status_code == 403
    assert qa.call("POST", base + "/apply-field", OWNER, {**body, "field": "confirmations"}).status_code == 422
    assert qa.call("POST", base + "/apply-field", OWNER, {k: v for k, v in body.items() if k != "answer_version"}).status_code == 422
    result = qa.call("POST", base + "/apply-field", OWNER, body)
    assert result.status_code == 200 and result.json()["requires_confirmation"]
    card = next(c for c in qa.records("card") if c["card"]["id"] == "published")
    assert card["revision"] == 2 and "data" not in card["card"]["confirmations"]
    assert card["card"]["data"] == suggestion["text"]
    assert card["snapshot"]["data"] == "Исходные данные подтверждены"
    assert card["specification"]["status"] == "stale" and card["specification"]["approved_at"] is None
    assert all(review_view(card, key)['status'] == 'stale' for key in ('review', 'nvidia_review'))
    assert card["evidence"]["data"]["source_id"].startswith("answer:")
    assert qa.call("POST", base + "/apply-field", OWNER, body).status_code == 409


def test_manual_transfer_keeps_honest_evidence_and_equal_text_still_revokes_confirmation(qa):
    question = qa.create()
    qa.answer(question, "Ответ отличается от уже подтверждённого текста")
    result = qa.call("POST", f"/api/questions/{question['id']}/apply-field", OWNER,
                    {"field": "data", "text": "Исходные данные подтверждены", "card_revision": 1, "answer_version": 1})
    assert result.status_code == 200
    card = next(c for c in qa.records("card") if c["card"]["id"] == "published")
    assert "data" not in card["card"]["confirmations"]
    assert card["evidence"]["data"]["source_id"].startswith("manual:")
    assert card["evidence"]["data"]["based_on_source_id"].startswith("answer:")


@pytest.mark.parametrize("suggestion", [
    {"field": "confirmations", "text": "Официальный ответ", "mode": "live"},
    {"field": "data", "text": "Выдуманный результат AI", "mode": "live"},
    {"field": "data", "text": "Официальный ответ"},
])
def test_invalid_or_invented_ai_suggestion_never_writes_card(factory, suggestion):
    qa = factory(lambda *_: suggestion)
    question = qa.create()
    qa.answer(question, "Официальный ответ")
    assert qa.call("POST", f"/api/questions/{question['id']}/suggest-field", OWNER).status_code == 502
    assert next(c for c in qa.records("card") if c["card"]["id"] == "published")["revision"] == 1


def test_suggestion_rechecks_revision_after_external_provider_returns(factory):
    qa = None
    def suggest(question, answer, card):
        with qa.store.transaction() as db:
            record = Store.get(db, "card", question["card_id"])
            record["revision"] += 1
            Store.put(db, "card", question["card_id"], record)
        return {"field": "data", "text": answer["text"], "mode": "live", "provider": "test"}
    qa = factory(suggest)
    question = qa.create()
    qa.answer(question)
    assert qa.call("POST", f"/api/questions/{question['id']}/suggest-field", OWNER).status_code == 409
