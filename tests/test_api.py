import pytest
from fastapi.testclient import TestClient
from app.main import create_app

B = {"X-Demo-Role": "business"}
T = {"X-Demo-Role": "team"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK", "1")
    with TestClient(create_app(tmp_path / "test.db", seed_demo=True)) as client:
        yield client


def build(client):
    response = client.post('/api/drafts', json={"text": "Need help answering customer questions", "industry": "Retail"}, headers=B)
    assert response.status_code == 201
    id = response.json()['id']
    questions = client.post(f'/api/drafts/{id}/clarify', headers=B).json()['questions']
    assert len(questions) >= 3
    answers = {q['id']: 'CSV with 100 synthetic questions' for q in questions if q['field'] == 'data'}
    response = client.post(f'/api/drafts/{id}/card', headers=B, json={'answers': answers})
    assert response.status_code == 200, response.text
    return response.json()


def mutate(client, card, action, body=None, method='post'):
    headers = {**B, 'If-Match': str(card['revision'])}
    return getattr(client, method)(f"/api/cards/{card['id']}" + action, headers=headers, json=body)


def test_human_confirmation_snapshot_and_stale_edit(client):
    card = build(client)
    assert card['rating']['total'] == 0 and card['mode'] == 'mock'
    assert mutate(client, card, '/publish').status_code == 422
    confirmed = mutate(client, card, '/confirm', {'fields': ['title', 'need', 'data']}).json()
    assert confirmed['rating']['total'] == 30
    assert mutate(client, card, '', {'changes': {'need': 'stale'}}, 'patch').status_code == 409
    published = mutate(client, confirmed, '/publish').json()
    assert published['published']
    edited = mutate(client, published, '', {'changes': {'data': 'Changed input'}}, 'patch').json()
    assert edited['rating']['total'] == 10 and 'data' not in edited['confirmed_fields']
    assert edited['has_unpublished_changes']
    public = next(c for c in client.get('/api/cards').json() if c['id'] == card['id'])
    assert public['rating']['total'] == 30 and public['data'] != edited['data']
    assert mutate(client, edited, '/publish').status_code == 422


def test_low_score_proposals_manual_choices_and_idempotent_milestone(client):
    cards = client.get('/api/cards').json()
    assert len(cards) == 5
    assert [c['rating']['total'] for c in cards] == [100, 82, 67, 49, 34]
    low = cards[-1]
    teams = client.get('/api/teams').json()
    ids = []
    for team in [teams[0], teams[1], teams[0]]:
        r = client.post(f"/api/cards/{low['id']}/proposals", headers=T, json={
            'team_id': team['id'], 'idea': 'A prototype', 'plan': 'Build and validate',
            'timeline': '3 days', 'prototype_url': 'https://example.com/demo'})
        assert r.status_code == 201
        ids.append(r.json()['id'])
    assert client.post(f'/api/proposals/{ids[0]}/milestone', headers=B).status_code == 409
    assert client.post(f'/api/proposals/{ids[0]}/decision', headers=T, json={'action':'select'}).status_code == 403
    for id in ids:
        assert client.post(f'/api/proposals/{id}/decision', headers=B, json={'action':'select'}).json()['status'] == 'selected'
    first = client.post(f'/api/proposals/{ids[0]}/milestone', headers=B).json()
    again = client.post(f'/api/proposals/{ids[2]}/milestone', headers=B).json()
    assert first == {'points':10, 'already_awarded':False}
    assert again == {'points':10, 'already_awarded':True}


def test_roles_validation_filter_and_persistence(client):
    assert client.post('/api/drafts', json={'text':'x','industry':'y'}).status_code == 403
    assert len(client.get('/api/cards?level=draft').json()) == 1
    card = build(client)
    assert client.patch(f"/api/cards/{card['id']}", headers=B, json={'changes':{'need':'x'}}).status_code == 428
    assert mutate(client, card, '', {'changes': {'confirmations': 'x'}}, 'patch').status_code == 422
    assert client.get('/').status_code == 200
    assert client.get('/static/api.js').status_code == 200
    with TestClient(create_app(client.app.state.store.path, seed_demo=True)) as reopened:
        assert reopened.get(f"/api/cards/{card['id']}").json()['id'] == card['id']
        assert len(reopened.get('/api/cards').json()) == 5


def test_proposal_keeps_conditions_after_republication(client):
    card = client.get('/api/cards').json()[-1]
    team = client.get('/api/teams').json()[0]
    proposal = client.post(f"/api/cards/{card['id']}/proposals", headers=T, json={
        'team_id':team['id'], 'idea':'Build', 'plan':'Prototype', 'timeline':'5 days',
        'prototype_url':'https://example.com/prototype'}).json()
    current = client.get(f"/api/cards/{card['id']}").json()
    edited = mutate(client, current, '', {'changes':{'title':'Changed conditions'}}, 'patch').json()
    confirmed = mutate(client, edited, '/confirm', {'fields':['title']}).json()
    assert mutate(client, confirmed, '/publish').status_code == 200
    saved = next(p for p in client.get(f"/api/cards/{card['id']}/proposals").json() if p['id'] == proposal['id'])
    assert saved['task_snapshot']['title'] == card['title']
    assert saved['task_snapshot']['revision'] == card['revision']


def test_concurrent_milestones_award_once(client):
    from concurrent.futures import ThreadPoolExecutor
    card = client.get('/api/cards').json()[0]
    proposal = client.get(f"/api/cards/{card['id']}/proposals").json()[0]
    url = f"/api/proposals/{proposal['id']}"
    client.post(url + '/decision', headers=B, json={'action':'select'})
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: client.post(url + '/milestone', headers=B).json(), range(4)))
    assert sum(not r['already_awarded'] for r in results) == 1
    assert all(r['points'] == 10 for r in results)
