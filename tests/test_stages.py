import pytest
from fastapi.testclient import TestClient
from app.main import create_app

B = {'X-Demo-Role': 'business'}
T = {'X-Demo-Role': 'team'}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv('MOCK', '1')
    app = create_app(tmp_path / 'stages.db', seed_demo=True)
    with TestClient(app) as c:
        card = c.get('/api/cards').json()[0]
        team = c.get('/api/teams').json()[0]
        p = c.post(f"/api/cards/{card['id']}/proposals", headers=T, json=dict(team_id=team['id'],
            idea='Synthetic stage', plan='Build', timeline='3 days', prototype_url='https://example.com/stage')).json()
        c.post(f"/api/proposals/{p['id']}/decision", headers=B, json={'action':'select'})
        yield c, card, p


def define(c, card, p):
    return c.post(f"/api/proposals/{p['id']}/stage", headers=B, json=dict(card_revision=card['revision'],
        expected_result='Search prototype', input_example='Two synthetic questions and supplied answers',
        verification_method='Business compares both answers with the supplied examples'))


def test_stage_round_trip_immutable_terms_and_idempotent_points(setup):
    c, card, p = setup
    path = f"/api/proposals/{p['id']}/stage"
    assert c.get(path).json() is None
    stage = define(c, card, p).json()
    assert stage['status'] == 'defined'
    assert define(c, card, p).status_code == 409
    assert c.post(f"/api/proposals/{p['id']}/milestone", headers=B).status_code == 409
    assert c.post(path+'/decision', headers=B, json=dict(version=1,action='accept',note='Looks good')).status_code == 409
    submit = dict(version=1,url='https://example.com/result',note='Implemented both cases')
    assert c.post(path+'/submission', headers=B, json=submit).status_code == 403
    sent = c.post(path+'/submission', headers=T, json=submit).json()
    assert c.post(path+'/submission', headers=T, json=submit).status_code == 409
    revise = c.post(path+'/decision', headers=B, json=dict(version=sent['version'],action='request_changes',note='Fix second answer')).json()
    assert revise['status'] == 'needs_changes'
    assert next(r for r in c.get(f"/api/cards/{card['id']}/proposals").json() if r['id']==p['id'])['progress_points'] == 0
    sent = c.post(path+'/submission', headers=T, json={**submit,'version':revise['version'],'note':'Second answer corrected'}).json()
    accept = dict(version=sent['version'],action='accept',note='Both examples match supplied answers')
    assert c.post(path+'/decision', headers=T, json=accept).status_code == 403
    accepted = c.post(path+'/decision', headers=B, json=accept).json()
    assert accepted['status'] == 'accepted'
    assert accepted['task_snapshot'] == stage['task_snapshot']
    assert len(accepted['history']) == 4
    assert c.post(path+'/decision', headers=B, json=accept).json() == accepted
    assert c.post(path+'/submission', headers=T, json={**submit,'version':accepted['version']}).status_code == 409
    assert c.post(f"/api/proposals/{p['id']}/milestone", headers=B).json() == {'points':10,'already_awarded':True}
    all_proposals = c.get(f"/api/cards/{card['id']}/proposals").json()
    assert all(r['progress_points'] == 10 for r in all_proposals if r['team_id'] == p['team_id'])


def test_stage_requires_selected_and_current_publication(setup):
    c, card, p = setup
    assert define(c, {**card, 'revision':card['revision']+1}, p).status_code == 409
    c.post(f"/api/proposals/{p['id']}/decision", headers=B, json={'action':'reject'})
    assert define(c, card, p).status_code == 409


def test_stage_keeps_conditions_after_card_edit_and_blocks_bad_url(setup):
    c, card, p = setup
    stage = define(c, card, p).json()
    c.patch(f"/api/cards/{card['id']}", headers={**B,'If-Match':str(card['revision'])},json={'changes':{'constraints':'Changed after agreement'}})
    path = f"/api/proposals/{p['id']}/stage"
    assert c.get(path).json()['task_snapshot'] == stage['task_snapshot']
    assert c.post(path+'/submission',headers=T,json=dict(version=1,url='javascript:alert(1)',note='test')).status_code == 422
    assert c.post(path+'/submission',headers=T,json=dict(version=1,url='https://example.com',note=' ')).status_code == 422


def test_existing_legacy_award_cannot_be_relabelled_as_verified(setup):
    c, card, p = setup
    assert c.post(f"/api/proposals/{p['id']}/milestone",headers=B).status_code == 200
    assert define(c, card, p).status_code == 409
