"""One immutable, versioned first-stage agreement per task/team; human acceptance."""
import json
from datetime import datetime, timezone
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import Field, HttpUrl
from app.schemas import Model, NonEmpty
from app.store import Store


class StageInput(Model):
    card_revision: int = Field(ge=1)
    expected_result: NonEmpty = Field(max_length=3000)
    input_example: NonEmpty = Field(max_length=3000)
    verification_method: NonEmpty = Field(max_length=3000)


class SubmissionInput(Model):
    version: int = Field(ge=1)
    url: HttpUrl
    note: NonEmpty = Field(max_length=3000)


class AcceptanceInput(Model):
    version: int = Field(ge=1)
    action: Literal['accept', 'request_changes']
    note: NonEmpty = Field(max_length=3000)


def stage_key(item):
    return json.dumps([item['task_id'], item['team_id'], 'prototype'])


def register_stages(app, store, require, business, student):
    def selected(db, id):
        item = require(db, 'proposal', id)
        if item['status'] != 'selected':
            raise HTTPException(409, 'Сначала бизнес должен выбрать команду')
        return item

    def current(db, item, version):
        stage = require(db, 'stage', stage_key(item))
        if stage['version'] != version:
            raise HTTPException(409, 'Этап изменился. Обновите его перед действием.')
        return stage

    @app.get('/api/proposals/{id}/stage')
    def get_stage(id: str):
        with store.transaction() as db:
            item = require(db, 'proposal', id)
            return Store.get(db, 'stage', stage_key(item))

    @app.post('/api/proposals/{id}/stage', dependencies=[Depends(business)], status_code=201)
    def define(id: str, body: StageInput):
        with store.transaction() as db:
            item = selected(db, id)
            key = stage_key(item)
            if Store.get(db, 'stage', key) or Store.get(db, 'milestone', key):
                raise HTTPException(409, 'Этап уже определён или баллы уже выданы. Обновите данные.')
            snapshot = require(db, 'card', item['task_id']).get('snapshot')
            if not snapshot or snapshot['revision'] != body.card_revision:
                raise HTTPException(409, 'Опубликованные условия изменились. Обновите задачу.')
            stage = {**body.model_dump(), 'task_snapshot': snapshot, 'proposal_id': id,
                     'task_id': item['task_id'], 'team_id': item['team_id'],
                     'version': 1, 'status': 'defined', 'submission': None, 'history': [],
                     'created_at': datetime.now(timezone.utc).isoformat(), 'created_by': 'demo-business'}
            Store.put(db, 'stage', key, stage)
            return stage

    @app.post('/api/proposals/{id}/stage/submission', dependencies=[Depends(student)])
    def submit(id: str, body: SubmissionInput):
        with store.transaction() as db:
            item = selected(db, id)
            stage = current(db, item, body.version)
            if stage['status'] not in ('defined', 'needs_changes'):
                raise HTTPException(409, 'Результат уже отправлен или принят')
            stage['submission'] = {'url': str(body.url), 'note': body.note,
                                   'submitted_at': datetime.now(timezone.utc).isoformat()}
            stage['history'].append({'event': 'submitted', **stage['submission']})
            stage.update(status='submitted', version=stage['version'] + 1)
            Store.put(db, 'stage', stage_key(item), stage)
            return stage

    @app.post('/api/proposals/{id}/stage/decision', dependencies=[Depends(business)])
    def accept(id: str, body: AcceptanceInput):
        with store.transaction() as db:
            item = selected(db, id)
            key = stage_key(item)
            existing = require(db, 'stage', key)
            if existing['status'] == 'accepted' and body.action == 'accept':
                return existing  # Idempotent retry never modifies the accepted evidence.
            stage = current(db, item, body.version)
            if stage['status'] != 'submitted':
                raise HTTPException(409, 'Команда ещё не отправила результат')
            stage.update(status='accepted' if body.action == 'accept' else 'needs_changes',
                         version=stage['version'] + 1, decision_note=body.note,
                         decided_at=datetime.now(timezone.utc).isoformat(), decided_by='demo-business')
            stage['history'].append({'event': stage['status'], 'note': body.note, 'at': stage['decided_at']})
            if body.action == 'accept':
                Store.put(db, 'milestone', key, {'points': 10, 'confirmed_by': 'demo-business',
                    'stage_version': stage['version'], 'accepted_at': stage['decided_at']})
                for p in Store.all(db, 'proposal'):
                    if p['task_id'] == item['task_id'] and p['team_id'] == item['team_id']:
                        p['progress_points'] = 10
                        Store.put(db, 'proposal', p['id'], p)
            Store.put(db, 'stage', key, stage)
            return stage
