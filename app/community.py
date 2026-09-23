"""Explicit demo sessions and transactional in-app notification delivery.

Demo account switching is NOT production authentication. Set COMMUNITY_DEMO=0
to disable it; unknown/missing sessions fail closed for all community endpoints.
"""
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, Response
from pydantic import Field

from app.schemas import Model
from app.store import Store


def now():
    return datetime.now(timezone.utc)


def demo_enabled():
    return os.getenv('COMMUNITY_DEMO', '1') == '1'


def audit(db, event, actor_id, entity_id, details=None):
    key = secrets.token_hex(16)
    Store.put(db, 'community_audit', key, {
        'id': key, 'event': event, 'actor_id': actor_id, 'entity_id': entity_id,
        'details': details or {}, 'at': now().isoformat(),
    })


def notify(db, recipient_id, kind, entity_id, payload=None, *, instant=None):
    payload = payload or {}
    identity = json.dumps([recipient_id, kind, entity_id, payload], sort_keys=True, ensure_ascii=False)
    key = hashlib.sha256(identity.encode()).hexdigest()
    if Store.get(db, 'community_outbox', key):
        return
    instant = instant or now()
    due = (instant.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
           if kind == 'new_question' else instant)
    Store.put(db, 'community_outbox', key, {
        'id': key, 'recipient_id': recipient_id, 'kind': kind, 'entity_id': entity_id,
        'payload': payload, 'created_at': instant.isoformat(), 'due_at': due.isoformat(), 'delivered': False,
    })


def seed_community(store):
    if not demo_enabled():
        return
    with store.transaction() as db:
        users = [
            {'id': 'demo-business', 'name': 'Заказчик · Sana Demo', 'role': 'business', 'company_id': 'demo-company', 'company_name': 'Sana Demo'},
            {'id': 'other-business', 'name': 'Заказчик · Другая компания', 'role': 'business', 'company_id': 'other-company', 'company_name': 'Другая компания'},
            {'id': 'demo-moderator', 'name': 'Модератор демо', 'role': 'moderator'},
        ]
        for team in Store.all(db, 'team'):
            for suffix, title in [('captain', 'Капитан'), ('member', 'Участник')]:
                users.append({'id': f"{team['id']}:{suffix}", 'name': f"{title} · {team['name']}",
                              'role': 'student', 'team_id': team['id'], 'captain': suffix == 'captain'})
        for user in users:
            if not Store.get(db, 'user', user['id']):
                Store.put(db, 'user', user['id'], {**user, 'synthetic': True})


def owner(db, card_record, actor):
    if actor.get('role') != 'business' or actor.get('company_id') != card_record.get('company_id', 'demo-company'):
        raise HTTPException(403, 'Действие доступно только владельцу компании этой задачи')


def deliver_notifications(store, instant=None):
    """Restart-safe inbox delivery. Never sends email or messages off-platform."""
    instant = instant or now()
    with store.transaction() as db:
        users = Store.all(db, 'user')
        for question in Store.all(db, 'card_question'):
            if question.get('status') != 'new' or not question.get('created_at'):
                continue
            if instant - datetime.fromisoformat(question['created_at']) < timedelta(hours=72):
                continue
            card = Store.get(db, 'card', question['card_id'])
            if not card:
                continue
            for user in users:
                if user.get('role') == 'business' and user.get('company_id') == card.get('company_id', 'demo-company'):
                    notify(db, user['id'], 'question_reminder', question['id'], {'card_id': question['card_id']}, instant=instant)
        for project in Store.all(db, 'project'):
            assessment = Store.get(db, 'project_assessment', project['id'])
            if (project.get('status') not in ('completed', 'closed_early') or not project.get('closed_at')
                    or (assessment and assessment.get('submitted_at'))):
                continue
            days = (instant - datetime.fromisoformat(project['closed_at'])).total_seconds() / 86400
            if days > 30:
                continue
            # On restart send only the latest due reminder, not a burst of old ones.
            due_day = max((day for day in (3, 7, 14) if days >= day), default=None)
            if due_day is None:
                continue
            for user in users:
                if user.get('role') == 'business' and user.get('company_id') == project.get('company_id', 'demo-company'):
                    notify(db, user['id'], 'assessment_reminder', project['id'], {'day': due_day}, instant=instant)
        digests = {}
        for entry in Store.all(db, 'community_outbox'):
            if entry['delivered'] or datetime.fromisoformat(entry['due_at']) > instant:
                continue
            if entry['kind'] == 'new_question':
                digests.setdefault((entry['recipient_id'], entry['due_at']), []).append(entry)
            else:
                Store.put(db, 'notification', entry['id'], {**entry, 'delivered_at': instant.isoformat(), 'read': False})
            entry['delivered'] = True
            Store.put(db, 'community_outbox', entry['id'], entry)
        for (recipient, due_at), entries in digests.items():
            key = hashlib.sha256(f'digest:{recipient}:{due_at}'.encode()).hexdigest()
            Store.put(db, 'notification', key, {
                'id': key, 'recipient_id': recipient, 'kind': 'question_digest',
                'entity_id': entries[0]['entity_id'], 'payload': {'question_ids': [e['entity_id'] for e in entries]},
                'delivered_at': instant.isoformat(), 'read': False,
            })


class SessionInput(Model):
    user_id: str = Field(min_length=1, max_length=200)


def register_community(app, store, require):
    def current(request):
        token = request.cookies.get('sana_session', '')
        if not token:
            return None
        with store.transaction() as db:
            session = Store.get(db, 'community_session', hashlib.sha256(token.encode()).hexdigest())
            if not session or (not demo_enabled() and session.get('demo', True)):
                return None
            try:
                expires = datetime.fromisoformat(session['expires_at'])
            except (KeyError, TypeError, ValueError):
                return None
            if expires.tzinfo is None or expires <= now() or not session.get('user_id'):
                return None
            return Store.get(db, 'user', session['user_id'])

    def actor(request: Request):
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.headers.get('X-Community-Request') != '1':
            raise HTTPException(403, 'Запрос должен быть отправлен из приложения')
        user = current(request)
        if not user:
            raise HTTPException(401, 'Выберите учётную запись в разделе сотрудничества')
        return user

    @app.get('/api/community')
    def community(request: Request):
        with store.transaction() as db:
            users = Store.all(db, 'user') if demo_enabled() else []
        return {'demo': demo_enabled(), 'users': users, 'actor': current(request),
                'notification_channel': 'in_app', 'authentication': 'demo_session' if demo_enabled() else 'session_required'}

    @app.post('/api/community/session')
    def session(body: SessionInput, request: Request, response: Response):
        if not demo_enabled() or request.headers.get('X-Community-Request') != '1':
            raise HTTPException(403, 'Переключение учебных учётных записей отключено')
        with store.transaction() as db:
            user = require(db, 'user', body.user_id)
            token = secrets.token_urlsafe(32)
            key = hashlib.sha256(token.encode()).hexdigest()
            Store.put(db, 'community_session', key, {'user_id': user['id'], 'demo': True,
                'expires_at': (now() + timedelta(hours=12)).isoformat()})
        response.set_cookie('sana_session', token, httponly=True, samesite='strict',
                            secure=request.url.scheme == 'https', max_age=43200)
        return {'actor': user, 'demo': True}

    @app.get('/api/notifications')
    def inbox(user=Depends(actor)):
        deliver_notifications(store)
        with store.transaction() as db:
            return sorted([n for n in Store.all(db, 'notification') if n['recipient_id'] == user['id']],
                          key=lambda n: n['delivered_at'], reverse=True)

    @app.post('/api/notifications/{id}/read')
    def read_notification(id: str, user=Depends(actor)):
        with store.transaction() as db:
            item = require(db, 'notification', id)
            if item['recipient_id'] != user['id']:
                raise HTTPException(403, 'Это уведомление другого пользователя')
            item['read'] = True
            Store.put(db, 'notification', id, item)
            return item

    @app.get('/api/community/audit')
    def audit_log(user=Depends(actor)):
        if user['role'] != 'moderator':
            raise HTTPException(403, 'Журнал доступен модератору')
        with store.transaction() as db:
            return Store.all(db, 'community_audit')

    return {'actor': actor, 'owner': owner, 'audit': audit, 'notify': notify}
