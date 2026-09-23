"""Session boundaries and deterministic, restart-safe in-app reminders."""
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.community import audit, deliver_notifications, notify, register_community, seed_community
from app.store import Store


HEADER = {"X-Community-Request": "1"}
BASE = datetime(2026, 9, 23, 8, 15, tzinfo=timezone.utc)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("COMMUNITY_DEMO", "1")
    clock = {"now": BASE}
    monkeypatch.setattr("app.community.now", lambda: clock["now"])
    store = Store(tmp_path / "community.sqlite3")
    with store.transaction() as db:
        Store.put(db, "team", "team", {"id": "team", "name": "Учебная команда"})
    seed_community(store)

    def require(db, kind, id):
        value = Store.get(db, kind, id)
        if value is None:
            raise HTTPException(404, "Не найдено")
        return value

    app = FastAPI()
    register_community(app, store, require)
    with TestClient(app) as client:
        yield store, client, clock


def sign_in(client, user="demo-business"):
    response = client.post("/api/community/session", json={"user_id": user}, headers=HEADER)
    assert response.status_code == 200
    return response


def records(store, kind):
    with store.transaction() as db:
        return Store.all(db, kind)


def test_sessions_fail_closed_and_use_opaque_httponly_tokens(env):
    store, client, _ = env
    assert client.get("/api/notifications").status_code == 401
    assert client.get("/api/notifications", headers={"X-Demo-Role": "business", "X-User-Id": "demo-business"}).status_code == 401
    client.cookies.set("sana_session", "demo-business")
    assert client.get("/api/notifications").status_code == 401
    client.cookies.clear()
    response = sign_in(client)
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    token = client.cookies.get("sana_session")
    assert token != "demo-business" and len(token) >= 40
    with store.transaction() as db:
        assert Store.get(db, "community_session", token) is None
        session = Store.get(db, "community_session", hashlib.sha256(token.encode()).hexdigest())
    assert session["user_id"] == "demo-business"
    assert client.get("/api/community").json()["actor"]["id"] == "demo-business"


def test_session_and_mutations_reject_csrf_without_custom_header(env):
    store, client, _ = env
    assert client.post("/api/community/session", json={"user_id": "demo-business"}).status_code == 403
    sign_in(client)
    with store.transaction() as db:
        notify(db, "demo-business", "question_answered", "q", {})
    item = client.get("/api/notifications").json()[0]
    assert client.post(f"/api/notifications/{item['id']}/read").status_code == 403
    assert client.post(f"/api/notifications/{item['id']}/read", headers=HEADER).status_code == 200


def test_sessions_expire_exactly_at_twelve_hours(env):
    _, client, clock = env
    sign_in(client)
    clock["now"] = BASE + timedelta(hours=12, microseconds=-1)
    assert client.get("/api/notifications").status_code == 200
    clock["now"] += timedelta(microseconds=1)
    assert client.get("/api/notifications").status_code == 401


@pytest.mark.parametrize("expires_at", ["bad-date", "2026-09-24T00:00:00", None])
def test_corrupt_or_timezone_missing_session_fails_closed(env, expires_at):
    store, client, _ = env
    sign_in(client)
    key = hashlib.sha256(client.cookies.get("sana_session").encode()).hexdigest()
    with store.transaction() as db:
        session = Store.get(db, "community_session", key)
        session["expires_at"] = expires_at
        Store.put(db, "community_session", key, session)
    assert client.get("/api/notifications").status_code == 401


def test_production_disables_picker_and_rejects_preexisting_demo_session(env, monkeypatch):
    _, client, _ = env
    sign_in(client, "demo-moderator")
    monkeypatch.setenv("COMMUNITY_DEMO", "0")
    info = client.get("/api/community").json()
    assert info["demo"] is False and info["users"] == [] and info["actor"] is None
    assert client.post("/api/community/session", headers=HEADER, json={"user_id": "demo-business"}).status_code == 403
    assert client.get("/api/community/audit").status_code == 401


def test_inbox_and_audit_are_scoped_to_identity(env):
    store, client, _ = env
    with store.transaction() as db:
        notify(db, "demo-business", "question_answered", "first", {})
        notify(db, "other-business", "question_answered", "second", {})
        audit(db, "answer.created", "demo-business", "answer-id")
    sign_in(client)
    own = client.get("/api/notifications").json()
    assert len(own) == 1 and own[0]["entity_id"] == "first"
    assert client.get("/api/community/audit").status_code == 403
    sign_in(client, "other-business")
    other = client.get("/api/notifications").json()
    assert len(other) == 1 and other[0]["entity_id"] == "second"
    assert client.post(f"/api/notifications/{own[0]['id']}/read", headers=HEADER).status_code == 403
    sign_in(client, "demo-moderator")
    assert client.get("/api/community/audit").json()[0]["event"] == "answer.created"


def test_questions_are_delivered_in_one_hourly_digest_per_owner_and_not_duplicated(env):
    store, _, clock = env
    with store.transaction() as db:
        notify(db, "demo-business", "new_question", "q1", {"card_id": "one"})
        notify(db, "demo-business", "new_question", "q2", {"card_id": "two"})
        notify(db, "other-business", "new_question", "q3", {"card_id": "three"})
        notify(db, "demo-business", "new_question", "q1", {"card_id": "one"})
    assert len(records(store, "community_outbox")) == 3
    boundary = BASE.replace(hour=9, minute=0)
    deliver_notifications(store, boundary - timedelta(microseconds=1))
    assert records(store, "notification") == []
    deliver_notifications(store, boundary)
    inbox = records(store, "notification")
    assert len(inbox) == 2
    business = next(item for item in inbox if item["recipient_id"] == "demo-business")
    assert set(business["payload"]["question_ids"]) == {"q1", "q2"}
    assert business["kind"] == "question_digest"
    # A new Store object represents a fresh process opening the same durable DB.
    resumed = Store(store.path)
    deliver_notifications(resumed, boundary + timedelta(minutes=20))
    assert records(resumed, "notification") == inbox
    clock["now"] = boundary + timedelta(minutes=10)
    with resumed.transaction() as db:
        notify(db, "demo-business", "new_question", "q4", {"card_id": "one"})
    deliver_notifications(resumed, boundary + timedelta(hours=1))
    assert len(records(resumed, "notification")) == 3


def test_unanswered_72_hour_reminder_is_once_and_only_for_owner(env):
    store, _, _ = env
    with store.transaction() as db:
        Store.put(db, "card", "card", {"company_id": "demo-company"})
        for qid, status in [("q-new", "new"), ("q-answered", "answered"), ("q-hidden", "hidden")]:
            Store.put(db, "card_question", qid,
                {"id": qid, "card_id": "card", "status": status, "created_at": BASE.isoformat()})
    due = BASE + timedelta(hours=72)
    deliver_notifications(store, due - timedelta(microseconds=1))
    assert records(store, "notification") == []
    deliver_notifications(store, due)
    first = records(store, "notification")
    assert len(first) == 1
    assert first[0]["recipient_id"] == "demo-business" and first[0]["entity_id"] == "q-new"
    assert first[0]["kind"] == "question_reminder"
    assert first[0]["created_at"] == due.isoformat()
    for instant in [due, due + timedelta(days=1), due + timedelta(days=30)]:
        deliver_notifications(Store(store.path), instant)
    assert records(store, "notification") == first


def test_assessment_reminders_day_3_7_14_once_and_stop_after_submission(env):
    store, _, _ = env
    with store.transaction() as db:
        Store.put(db, "project", "p", {"id": "p", "status": "completed", "closed_at": BASE.isoformat(), "company_id": "demo-company"})
    deliver_notifications(store, BASE + timedelta(days=3, microseconds=-1))
    assert records(store, "notification") == []
    for day in [3, 3, 6, 7, 7, 13, 14, 14, 29, 31]:
        deliver_notifications(Store(store.path), BASE + timedelta(days=day))
    reminders = records(store, "notification")
    assert len(reminders) == 3
    assert {n["payload"]["day"] for n in reminders} == {3, 7, 14}
    assert all(n["kind"] == "assessment_reminder" and n["recipient_id"] == "demo-business" for n in reminders)
    with store.transaction() as db:
        Store.put(db, "project", "p-early", {"id": "p-early", "status": "closed_early", "closed_at": BASE.isoformat(), "company_id": "demo-company"})
        Store.put(db, "project_assessment", "p-early", {"submitted_at": (BASE + timedelta(days=1)).isoformat()})
    deliver_notifications(store, BASE + timedelta(days=14))
    assert len(records(store, "notification")) == 3


def test_reminder_restart_skips_old_due_days_and_active_projects(env):
    store, _, _ = env
    with store.transaction() as db:
        for pid, status in [("closed", "closed_early"), ("active", "active")]:
            Store.put(db, "project", pid, {"id": pid, "status": status, "closed_at": BASE.isoformat(), "company_id": "demo-company"})
    deliver_notifications(Store(store.path), BASE + timedelta(days=14))
    notices = records(store, "notification")
    assert len(notices) == 1 and notices[0]["entity_id"] == "closed"
    assert notices[0]["payload"]["day"] == 14
    deliver_notifications(Store(store.path), BASE + timedelta(days=31))
    assert records(store, "notification") == notices


def test_draft_assessment_does_not_suppress_due_reminder(env):
    store, _, _ = env
    with store.transaction() as db:
        Store.put(db, "project", "p", {"id": "p", "status": "completed", "closed_at": BASE.isoformat(), "company_id": "demo-company"})
        Store.put(db, "project_assessment", "p", {"answers": {}, "submitted_at": None})
    deliver_notifications(store, BASE + timedelta(days=3))
    notices = records(store, "notification")
    assert len(notices) == 1 and notices[0]["payload"]["day"] == 3
    with store.transaction() as db:
        Store.put(db, "project_assessment", "p", {"answers": {}, "submitted_at": (BASE + timedelta(days=4)).isoformat()})
    deliver_notifications(Store(store.path), BASE + timedelta(days=7))
    assert records(store, "notification") == notices
