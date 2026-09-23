"""Acceptance tests for assessments, ownership, provenance and immutable PDFs."""
import copy
import io
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.community import register_community, seed_community
from app.project_letters import now, plain, register_project_letters
from app.stages import stage_key
from app.store import Store


HEADERS = {"X-Community-Request": "1"}
OWNER = "demo-business"
CAPTAIN = "team-one:captain"
MEMBER = "team-one:member"
OTHER = "team-two:captain"
EXAMPLE = "Команда разработала рабочую форму регистрации: заявки сохраняются, а повторный адрес проверяется."


def assessment(**changes):
    value = {"answers": {"q1": "meets", "q2": ["prototype", "testing"], "q3": ["responsibility"],
        "q4": "meets", "q5": "testing", "q6": "yes", "q7": "no"},
        "comments": {"q1": "Результат соответствует согласованной задаче.", "q2": EXAMPLE},
        "highlighted_user_ids": []}
    for key, data in changes.items():
        value[key] = data
    return value


class Harness:
    def __init__(self, path):
        self.store = Store(path)
        self.app = FastAPI()
        with self.store.transaction() as db:
            for id in ("team-one", "team-two"):
                Store.put(db, "team", id, {"id": id, "name": id})
            Store.put(db, "card", "card-one", {"card": {"title": "Регистрация студентов"},
                "snapshot": {"title": "Регистрация студентов"}})
            self.proposal = {"id": "proposal-one", "team_id": "team-one", "task_id": "card-one",
                "status": "selected", "progress_points": 10, "created_at": "2026-09-20T08:30:00+00:00"}
            Store.put(db, "proposal", "proposal-one", self.proposal)
        seed_community(self.store)

        def require(db, kind, id):
            value = Store.get(db, kind, id)
            if value is None:
                raise HTTPException(404, "Не найдено")
            return value

        helpers = register_community(self.app, self.store, require)
        register_project_letters(self.app, self.store, require, **helpers)
        self.client = TestClient(self.app)

    def login(self, user=OWNER, client=None):
        client = client or self.client
        result = client.post("/api/community/session", headers=HEADERS, json={"user_id": user})
        assert result.status_code == 200, result.text
        return client

    def call(self, method, path, body=None, user=OWNER):
        self.login(user)
        return self.client.request(method, path, headers=HEADERS, json=body)

    def project(self):
        result = self.call("POST", "/api/proposals/proposal-one/project")
        assert result.status_code == 201, result.text
        return result.json()

    def roster(self, project=None, confirm=True):
        project = project or self.project()
        result = self.call("PUT", f"/api/projects/{project['id']}/roles", {"members": [
            {"user_id": CAPTAIN, "role": "Разработчик"}, {"user_id": MEMBER, "role": "Дизайнер"}]}, CAPTAIN)
        assert result.status_code == 200, result.text
        if confirm:
            result = self.call("POST", f"/api/projects/{project['id']}/roles/confirm", {"expected_role": "Разработчик"}, CAPTAIN)
            assert result.status_code == 200, result.text
        return result.json()

    def closed(self):
        project = self.roster()
        result = self.call("POST", f"/api/projects/{project['id']}/close", {"status": "closed_early"})
        assert result.status_code == 200, result.text
        return result.json()

    def preview(self, project=None, data=None, language="ru"):
        project = project or self.closed()
        result = self.call("PUT", f"/api/projects/{project['id']}/assessment", data or assessment())
        assert result.status_code == 200, result.text
        result = self.call("GET", f"/api/projects/{project['id']}/letter/preview?language={language}")
        assert result.status_code == 200, result.text
        return result.json()

    def issue(self, draft=None):
        draft = draft or self.preview()
        result = self.call("POST", f"/api/letters/{draft['id']}/issue", {"signer_name": "Айдана Тестова", "signer_position": "Руководитель"})
        assert result.status_code == 201, result.text
        return result.json()

    def record(self, kind, id):
        with self.store.transaction() as db:
            return Store.get(db, kind, id)

    def update(self, kind, id, value):
        with self.store.transaction() as db:
            Store.put(db, kind, id, value)


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("COMMUNITY_DEMO", "1")
    monkeypatch.setenv("APP_PUBLIC_URL", "https://sana.example")
    harness = Harness(tmp_path / "letters.db")
    yield harness
    harness.client.close()


def test_requires_session_and_company_ownership(api):
    assert api.client.get("/api/projects", headers={"X-Demo-Role": "business"}).status_code == 401
    assert api.call("POST", "/api/proposals/proposal-one/project", user=OTHER).status_code == 403
    assert api.call("POST", "/api/proposals/proposal-one/project", user="other-business").status_code == 403
    assert api.call("POST", "/api/proposals/proposal-one/project", user=MEMBER).status_code == 403
    project = api.project()
    assert api.call("GET", f"/api/projects/{project['id']}", user=OTHER).status_code == 403
    assert api.call("POST", f"/api/projects/{project['id']}/close", {"status": "closed_early"}, CAPTAIN).status_code == 403
    assert api.client.put(f"/api/projects/{project['id']}/roles", json={"members": []}).status_code == 403


def test_project_is_stable_for_selected_pair_and_get_is_readonly(api):
    assert api.call("GET", "/api/proposals/proposal-one/project").status_code == 404
    project = api.project()
    assert api.project()["id"] == project["id"]
    second = {**api.proposal, "id": "proposal-duplicate"}
    api.update("proposal", second["id"], second)
    assert api.call("POST", "/api/proposals/proposal-duplicate/project").json()["id"] == project["id"]
    other = {**api.proposal, "id": "pending", "status": "pending"}
    api.update("proposal", "pending", other)
    assert api.call("POST", "/api/proposals/pending/project").status_code == 409
    assert len(api.call("GET", "/api/projects", user=CAPTAIN).json()) == 1
    assert api.call("GET", "/api/projects", user=OTHER).json() == []


def test_roles_actual_members_only_and_confirmation_resets_on_change(api):
    project = api.project()
    url = f"/api/projects/{project['id']}/roles"
    invalid = {"members": [{"user_id": OTHER, "role": "Разработчик"}]}
    assert api.call("PUT", url, invalid, CAPTAIN).status_code == 422
    assert api.call("PUT", url, {"members": []}, MEMBER).status_code == 403
    project = api.roster(project)
    captain = next(m for m in project["members"] if m["user_id"] == CAPTAIN)
    assert captain["confirmed_at"]
    result = api.call("PUT", url, {"members": [{"user_id": CAPTAIN, "role": "<b>Аналитик</b>"}]}, CAPTAIN)
    assert result.status_code == 200
    assert result.json()["members"][0]["confirmed_at"] is None
    assert result.json()["members"][0]["role"] == "Аналитик"
    assert api.call("POST", url + "/confirm", {"expected_role": "Дизайнер"}, MEMBER).status_code == 404
    assert api.call("POST", url + "/confirm", {"expected_role": "Дизайнер"}, OTHER).status_code == 403
    assert api.call("POST", url + "/confirm", {"expected_role": "Разработчик"}, CAPTAIN).status_code == 409
    assert api.call("POST", url + "/confirm", {"expected_role": "Аналитик"}, CAPTAIN).status_code == 200


def test_completed_requires_accepted_stage_not_progress_points(api):
    project = api.project()
    url = f"/api/projects/{project['id']}/close"
    assert api.call("POST", url, {"status": "completed"}).status_code == 409
    stage = {"status": "accepted", "decided_at": "2026-09-23T08:00:00+00:00", "created_at": "2026-09-21T08:00:00+00:00",
        "expected_result": "Регистрация сохраняется", "version": 3}
    api.update("stage", stage_key(project), stage)
    result = api.call("POST", url, {"status": "completed"})
    assert result.status_code == 200
    closed_at = result.json()["closed_at"]
    assert api.call("POST", url, {"status": "completed"}).json()["closed_at"] == closed_at
    assert api.call("POST", url, {"status": "closed_early"}).status_code == 409


def test_questionnaire_open_only_after_closure_and_for_30_days(api):
    project = api.roster()
    url = f"/api/projects/{project['id']}"
    assert api.call("GET", url + "/questionnaire").status_code == 409
    assert api.call("PUT", url + "/assessment", assessment()).status_code == 409
    assert api.call("GET", url + "/questionnaire", user=CAPTAIN).status_code == 403
    api.call("POST", url + "/close", {"status": "closed_early"})
    assert api.call("GET", url + "/questionnaire").status_code == 200
    assert api.call("PUT", url + "/roles", {"members": []}, CAPTAIN).status_code == 409
    assert api.call("POST", url + "/roles/confirm", {"expected_role": "Разработчик"}, CAPTAIN).status_code == 409
    stored = api.record("project", project["id"])
    stored["closed_at"] = (now() - timedelta(days=31)).isoformat()
    api.update("project", project["id"], stored)
    assert api.call("GET", url + "/questionnaire").status_code == 410
    assert api.call("PUT", url + "/assessment", assessment()).status_code == 410


@pytest.mark.parametrize("change", [
    lambda a: a["comments"].update(q2="Мало"),
    lambda a: a["comments"].update(q2="я" * 501),
    lambda a: a["comments"].update(q9="я" * 1001),
    lambda a: a["answers"].update(q3=["responsibility", "initiative", "learning", "analysis"]),
    lambda a: a["answers"].update(q2=[]),
    lambda a: a["answers"].update(q1="invented"),
    lambda a: a.update(highlighted_user_ids=[MEMBER]),
    lambda a: a.update(highlighted_user_ids=[CAPTAIN, CAPTAIN]),
])
def test_assessment_validation(api, change):
    project = api.closed()
    data = assessment()
    change(data)
    assert api.call("PUT", f"/api/projects/{project['id']}/assessment", data).status_code == 422
    assert api.record("project_assessment", project["id"]) is None


def test_recommendation_no_blocks_preview_and_stale_issue(api):
    draft = api.preview()
    data = assessment()
    data["answers"]["q6"] = "no"
    pid = draft["project_id"]
    assert api.call("PUT", f"/api/projects/{pid}/assessment", data).status_code == 200
    assert api.call("GET", f"/api/projects/{pid}/letter/preview").status_code == 409
    assert api.call("POST", f"/api/letters/{draft['id']}/issue", {"signer_name": "Имя", "signer_position": "Должность"}).status_code == 409


@pytest.mark.parametrize("language", ["ru", "kk", "en"])
def test_sentence_provenance_and_verbatim_comments(api, language):
    data = assessment()
    data["comments"].update(q9="<b>Точный комментарий.</b><script>не показывать</script>", q7="Не обещаем стажировку")
    data["highlighted_user_ids"] = [CAPTAIN]
    draft = api.preview(data=data, language=language)
    assert draft["mode"] == "template" and draft["ai_used"] is False
    assert len(draft["members"]) == 1 and draft["members"][0]["user_id"] == CAPTAIN
    assert not any(s["source"]["question_id"] == "q7" for s in draft["sentences"])
    for sentence in draft["sentences"]:
        source = sentence["source"]
        assert source["question_id"] in {"q" + str(i) for i in range(1, 10)}
        assert source["template_version"] == "1"
        if source["kind"] == "comment":
            assert sentence["text"] == source["value"]
    assert EXAMPLE in draft["body_text"]
    assert "Точный комментарий." in draft["body_text"]
    assert "не показывать" not in draft["body_text"]
    assert "Не обещаем стажировку" not in draft["body_text"]
    assert draft["header"]["stages"] == []


def test_personal_pdf_qr_under_5s_and_frozen_bytes(api):
    draft = api.preview(language="kk")
    started = time.perf_counter()
    letter = api.issue(draft)
    assert time.perf_counter() - started < 5
    assert len(letter["copies"]) == 1
    item = letter["copies"][0]
    assert item["verify_url"].startswith("https://sana.example/verify/")
    assert item["show_in_portfolio"] is False
    response = api.call("GET", item["pdf_url"], user=CAPTAIN)
    assert response.status_code == 200 and response.content.startswith(b"%PDF")
    reader = PdfReader(io.BytesIO(response.content))
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert "Ұсыным хат" in text and "Разработчик" in text and EXAMPLE in text.replace("\n", " ")
    assert item["verify_url"] in text.replace("\n", "")
    data = assessment()
    data["comments"]["q2"] = "Обновлённый факт о результате: теперь в форме добавлена выгрузка зарегистрированных заявок в таблицу."
    api.call("PUT", f"/api/projects/{letter['project_id']}/assessment", data)
    assert api.call("GET", item["pdf_url"], user=CAPTAIN).content == response.content
    assert api.call("GET", item["pdf_url"], user=MEMBER).status_code == 403
    assert api.call("GET", item["pdf_url"], user="other-business").status_code == 403
    assert api.call("POST", f"/api/letters/{draft['id']}/issue", {"signer_name": "Имя", "signer_position": "Роль"}).status_code == 409


def test_issue_rolls_back_on_pdf_failure(api, monkeypatch):
    draft = api.preview()
    def unavailable(*args):
        raise RuntimeError("font unavailable")
    monkeypatch.setattr("app.project_letters.recommendation_pdf", unavailable)
    result = api.call("POST", f"/api/letters/{draft['id']}/issue", {"signer_name": "Имя", "signer_position": "Роль"})
    assert result.status_code == 503
    with api.store.transaction() as db:
        assert Store.all(db, "recommendation_letter") == []
        assert Store.all(db, "letter_copy") == []


def test_reissue_revoke_and_hidden_copy_verification(api):
    first = api.issue()
    item = first["copies"][0]
    url = "/verify/" + item["verify_code"] + "?format=json"
    assert api.client.get(url).json()["status"] == "valid"
    assert api.client.get("/api/users/" + CAPTAIN + "/portfolio").json() == []
    assert api.call("PATCH", "/api/letter-copies/" + item["id"] + "/visibility", {"show_in_portfolio": True}, MEMBER).status_code == 403
    assert api.call("PATCH", "/api/letter-copies/" + item["id"] + "/visibility", {"show_in_portfolio": True}, CAPTAIN).status_code == 200
    assert len(api.client.get("/api/users/" + CAPTAIN + "/portfolio").json()) == 1
    draft = api.call("GET", f"/api/projects/{first['project_id']}/letter/preview?language=en").json()
    second = api.call("POST", f"/api/letters/{first['id']}/reissue", {"draft_id": draft["id"], "signer_name": "Имя", "signer_position": "Роль", "language": "en"})
    assert second.status_code == 201, second.text
    second = second.json()
    assert second["version"] == 2
    assert api.client.get(url).json()["status"] == "replaced"
    assert api.client.get(url).json()["replaced_by_id"] == second["id"]
    assert api.call("POST", f"/api/letters/{first['id']}/reissue", {"draft_id": draft["id"], "signer_name": "Имя", "signer_position": "Роль"}).status_code == 409
    assert api.call("POST", f"/api/letters/{second['id']}/revoke", {"reason": "Фактическая ошибка"}, "other-business").status_code == 403
    assert api.call("POST", f"/api/letters/{second['id']}/revoke", {"reason": "Фактическая ошибка"}).status_code == 200
    assert api.client.get("/verify/" + second["copies"][0]["verify_code"] + "?format=json").json()["status"] == "revoked"
    assert api.record("recommendation_letter", first["id"])["body_text"] == first["body_text"]


def test_public_consent_only_fate_q1_comment_and_private_assessment(api):
    letter = api.issue()
    url = "/api/teams/team-one/project-recommendations"
    assert api.client.get(url).json() == []
    path = f"/api/projects/{letter['project_id']}/public-consent"
    assert api.call("PUT", path, {"public_consent": True}, MEMBER).status_code == 403
    assert api.call("PUT", path, {"public_consent": True}, OWNER).status_code == 403
    assert api.call("PUT", path, {"public_consent": True}, CAPTAIN).status_code == 200
    public = api.client.get(url).json()[0]
    assert set(public) == {"project_id", "prototype_fate", "result_comment"}
    assert public["prototype_fate"] == "testing"
    private = api.call("GET", f"/api/projects/{letter['project_id']}", user=CAPTAIN).json()
    assert private["assessment"] is None
    assert "assessment_snapshot" not in private["letters"][0]
    assert api.call("PUT", path, {"public_consent": False}, CAPTAIN).status_code == 200
    assert api.client.get(url).json() == []


def test_reissue_rejects_assessment_changed_since_shown_preview(api):
    first = api.issue()
    pid = first["project_id"]
    draft = api.call("GET", f"/api/projects/{pid}/letter/preview").json()
    data = assessment()
    data["comments"]["q2"] = "Новое описание результатов: команда разработала экспорт записей в таблицу и проверила выгрузку."
    assert api.call("PUT", f"/api/projects/{pid}/assessment", data).status_code == 200
    response = api.call("POST", f"/api/letters/{first['id']}/reissue", {"draft_id": draft["id"],
        "signer_name": "Имя", "signer_position": "Роль", "language": "ru"})
    assert response.status_code == 409
    assert api.record("recommendation_letter", first["id"])["status"] == "issued"


def test_reissue_never_reuses_earlier_draft_version(api):
    initial = api.preview()
    first = api.issue(initial)
    body = {"draft_id": initial["id"], "signer_name": "Имя", "signer_position": "Роль", "language": "ru"}
    assert api.call("POST", f"/api/letters/{first['id']}/reissue", body).status_code == 409
    new_draft = api.call("GET", f"/api/projects/{first['project_id']}/letter/preview").json()
    body["draft_id"] = new_draft["id"]
    second = api.call("POST", f"/api/letters/{first['id']}/reissue", body)
    assert second.status_code == 201 and second.json()["version"] == 2
    body["draft_id"] = initial["id"]
    assert api.call("POST", f"/api/letters/{second.json()['id']}/reissue", body).status_code == 409
    assert api.record("recommendation_letter", second.json()["id"])["version"] == 2


def test_plain_nested_entities_and_surrogates_are_safe():
    assert plain("&amp;lt;script&amp;gt;hidden&amp;lt;/script&amp;gt;<b>Результат</b>\ud800") == "Результат"


def test_public_portfolio_page_only_visible_copies_and_escapes_text(api):
    letter = api.issue()
    item = letter["copies"][0]
    path = f"/profiles/users/{CAPTAIN}"
    with TestClient(api.app) as guest:
        hidden = guest.get(path)
        assert hidden.status_code == 200
        assert item["verify_code"] not in hidden.text
        assert letter["header"]["title"] not in hidden.text
        assert EXAMPLE not in hidden.text
        api.call("PATCH", f"/api/letter-copies/{item['id']}/visibility", {"show_in_portfolio": True}, CAPTAIN)
        stored = api.record("letter_copy", item["id"])
        stored["name"] = '<img src=x onerror="alert(1)">Участник'
        api.update("letter_copy", item["id"], stored)
        shown = guest.get(path + "?lang=kk")
        assert shown.status_code == 200 and '<html lang="kk">' in shown.text
        assert "Қатысушы портфолиосы" in shown.text
        assert item["verify_code"] in shown.text and letter["header"]["title"] in shown.text
        assert '<img' not in shown.text and '&lt;img' in shown.text
        assert EXAMPLE not in shown.text
        assert '/static/ui.css' in shown.text and 'href="/"' in shown.text
        assert "no-store" == shown.headers["Cache-Control"]
        api.call("PATCH", f"/api/letter-copies/{item['id']}/visibility", {"show_in_portfolio": False}, CAPTAIN)
        assert item["verify_code"] not in guest.get(path).text
        assert guest.get("/profiles/users/unknown").status_code == 404


def test_public_team_profile_only_consented_fate_and_q1_comment(api):
    letter = api.issue()
    pid = letter["project_id"]
    path = "/profiles/teams/team-one"
    with TestClient(api.app) as guest:
        hidden = guest.get(path)
        assert hidden.status_code == 200
        assert assessment()["comments"]["q1"] not in hidden.text and EXAMPLE not in hidden.text
        api.call("PUT", f"/api/projects/{pid}/public-consent", {"public_consent": True}, CAPTAIN)
        stored = api.record("project_assessment", pid)
        stored["comments"]["q1"] = '<script>alert(1)</script>Публичный отзыв'
        stored["comments"]["q9"] = "СЕКРЕТНЫЙ КОММЕНТАРИЙ"
        api.update("project_assessment", pid, stored)
        shown = guest.get(path + "?lang=kk")
        assert shown.status_code == 200 and '<html lang="kk">' in shown.text
        assert "Сынап жатырмыз" in shown.text and "Публичный отзыв" in shown.text
        assert '<script>' not in shown.text and '&lt;script&gt;' in shown.text
        assert EXAMPLE not in shown.text and "СЕКРЕТНЫЙ КОММЕНТАРИЙ" not in shown.text
        assert letter["copies"][0]["verify_code"] not in shown.text
        assert letter["header"]["title"] not in shown.text
        api.call("PUT", f"/api/projects/{pid}/public-consent", {"public_consent": False}, CAPTAIN)
        assert "Публичный отзыв" not in guest.get(path).text
        assert guest.get("/profiles/teams/unknown").status_code == 404


def test_complaint_notifies_moderator_and_actions_are_audited(api):
    letter = api.issue()
    cid = letter["copies"][0]["id"]
    path = f"/api/letter-copies/{cid}/complaint"
    assert api.call("POST", path, {"text": "В роли ошибка"}, MEMBER).status_code == 403
    result = api.call("POST", path, {"text": "<b>В роли ошибка</b>"}, CAPTAIN)
    assert result.status_code == 201 and result.json()["text"] == "В роли ошибка"
    with api.store.transaction() as db:
        events = {row["event"] for row in Store.all(db, "community_audit")}
        notices = Store.all(db, "community_outbox")
    assert {"project_created", "project_roles_updated", "project_role_confirmed", "project_closed", "project_assessment_submitted", "letter_issued", "letter_complaint_created"} <= events
    assert any(n["kind"] == "letter_issued" and n["recipient_id"] == CAPTAIN for n in notices)
    assert any(n["kind"] == "letter_complaint" and n["recipient_id"] == "demo-moderator" for n in notices)
    assert next(n for n in notices if n["kind"] == "letter_complaint")["payload"]["text"] == "В роли ошибка"
    for user in (OWNER, CAPTAIN, MEMBER, OTHER):
        assert api.call("GET", "/api/letter-complaints", user=user).status_code == 403
    reports = api.call("GET", "/api/letter-complaints", user="demo-moderator")
    assert reports.status_code == 200
    assert reports.json() == [result.json()]
    assert reports.json()[0]["text"] == "В роли ошибка"


def test_concurrent_issue_produces_one_version(api):
    draft = api.preview()
    clients = [api.login(client=TestClient(api.app)) for _ in range(2)]
    def issue(client):
        return client.post(f"/api/letters/{draft['id']}/issue", headers=HEADERS,
            json={"signer_name": "Имя", "signer_position": "Роль"}).status_code
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(issue, clients))
        assert sorted(results) == [201, 409]
    finally:
        for client in clients:
            client.close()
    with api.store.transaction() as db:
        assert len(Store.all(db, "recommendation_letter")) == 1


def test_public_verification_escapes_input_and_untrusted_host_not_used(api):
    draft = api.preview()
    api.login()
    result = api.client.post(f"/api/letters/{draft['id']}/issue", headers={**HEADERS, "Host": "evil.invalid"},
        json={"signer_name": "&lt;img src=x onerror=alert(1)&gt;Имя", "signer_position": "Директор"})
    # A different Host can legitimately stop a host-scoped session cookie.
    if result.status_code == 401:
        result = api.call("POST", f"/api/letters/{draft['id']}/issue", {"signer_name": "&lt;img src=x onerror=alert(1)&gt;Имя", "signer_position": "Директор"})
    assert result.status_code == 201, result.text
    letter = result.json()
    assert letter["signer_name"] == "Имя"
    assert letter["copies"][0]["verify_url"].startswith("https://sana.example/")
    page = api.client.get("/verify/" + letter["copies"][0]["verify_code"])
    assert page.status_code == 200 and "<img" not in page.text
    assert "Действительно" in page.text and "Content-Security-Policy" in page.headers
    assert api.client.get("/verify/unknown?format=json").status_code == 404
