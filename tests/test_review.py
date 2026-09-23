from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.llm import Extractor
from app.review import CardReviewer, ReviewResult, validate_review, rule_issues
from app.schemas import CardContent
from app.insights import catalog_insights

B = {'X-Demo-Role': 'business'}


def build(client):
    draft = client.post('/api/drafts', headers=B, json={
        'text': 'Синтетическая задача: нужен помощник магазина', 'industry': 'Учебная', 'synthetic': True}).json()
    client.post(f"/api/drafts/{draft['id']}/clarify", headers=B)
    return client.post(f"/api/drafts/{draft['id']}/card", headers=B, json={'answers': {}}).json()


def action(client, card, suffix, body=None, method='post'):
    return getattr(client, method)(f"/api/cards/{card['id']}" + suffix,
        headers={**B, 'If-Match': str(card['revision'])}, json=body)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('MOCK', '1')
    monkeypatch.setenv('LLM_LOG_PATH', str(tmp_path / 'calls.jsonl'))
    with TestClient(create_app(tmp_path / 'review.db', seed_demo=False)) as client:
        yield client


def test_review_is_read_only_versioned_and_requires_business(client):
    card = build(client)
    assert card['review']['status'] == 'not_run'
    path = f"/api/cards/{card['id']}/review"
    assert client.post(path).status_code == 403
    assert client.post(path, headers=B).status_code == 428
    card = action(client, card, '', {'changes': {'data': 'Данные обсудим позже'}}, 'patch').json()
    checked = action(client, card, '/review').json()
    assert checked['review']['mode'] == 'mock'
    assert checked['review']['issues'][0]['quote'] == 'Данные обсудим позже'
    assert checked['revision'] == card['revision']
    assert checked['rating'] == card['rating'] and checked['confirmed_fields'] == card['confirmed_fields']
    assert all(checked[f] == card[f] for f in CardContent.model_fields)
    confirmed = action(client, checked, '/confirm', {'fields': ['title', 'need', 'data']}).json()
    assert confirmed['review']['status'] == 'complete'
    published = action(client, confirmed, '/publish').json()
    public = client.get('/api/cards').json()[0]
    assert public['catalog_insights']['review']['revision'] == published['revision']
    edited = action(client, published, '', {'changes': {'data': 'CSV из 20 учебных вопросов'}}, 'patch').json()
    assert edited['review']['status'] == 'stale'
    assert action(client, published, '/review').status_code == 409
    rechecked = action(client, edited, '/review').json()
    assert rechecked['review']['status'] == 'complete'
    assert all(i['field'] != 'data' for i in rechecked['review']['issues'])
    assert client.get('/api/cards').json()[0]['data'] == public['data']
    # Unpublished critique/text cannot leak to the catalogue.
    assert client.get('/api/cards').json()[0]['catalog_insights']['review'] == public['catalog_insights']['review']


def test_review_race_does_not_save_result_for_changed_card(tmp_path, monkeypatch):
    monkeypatch.setenv('MOCK', '1')
    class RacingReviewer:
        def review(self, fields):
            response = action(client, card, '', {'changes': {'data': 'A new saved value'}}, 'patch')
            assert response.status_code == 200
            return dict(status='complete', mode='mock', provider='mock', issues=[])
    with TestClient(create_app(tmp_path / 'race.db', seed_demo=False, reviewer=RacingReviewer())) as client:
        card = build(client)
        assert action(client, card, '/review').status_code == 409
        actual = client.get(f"/api/cards/{card['id']}").json()
        assert actual['data'] == 'A new saved value'
        assert actual['review']['status'] == 'not_run'


def test_unavailable_review_does_not_change_card(tmp_path, monkeypatch):
    monkeypatch.setenv('MOCK', '1')
    class BrokenReviewer:
        def review(self, fields):
            raise RuntimeError('do not expose provider internals')
    with TestClient(create_app(tmp_path / 'failed.db', seed_demo=False, reviewer=BrokenReviewer())) as client:
        card = build(client)
        result = action(client, card, '/review')
        assert result.status_code == 503
        assert 'internals' not in result.text
        assert client.get(f"/api/cards/{card['id']}").json() == card


def test_quote_validation_rejects_invention_wrong_field_and_duplicates():
    fields = CardContent(data='Only annual totals', need='Monthly forecast').model_dump()
    issue = dict(field='data', quote='Only annual totals', message='Possible gap', question='Is monthly history available?')
    assert validate_review({'issues': [issue]}, fields).issues
    for changes in [{'quote': 'invented'}, {'field': 'users'}, {'quote': ''}]:
        with pytest.raises(ValueError):
            validate_review({'issues': [{**issue, **changes}]}, fields)
    with pytest.raises(ValueError):
        validate_review({'issues': [issue, issue]}, fields)
    assert validate_review({'issues': []}, fields).issues == []


@pytest.mark.parametrize('data,expected', [('', True), ('Обсудим позже', True),
    ('Уточним позже', True), ('Нет данных; бизнес подготовит учебный пример', False),
    ('CSV из 20 синтетических вопросов, доступ через учебный репозиторий', False),
    ('Доступ только к обезличенным строкам по согласованию с куратором', False)])
def test_demo_rules_do_not_claim_semantic_analysis(data, expected):
    fields = CardContent(data=data, success_criteria='Проверка по 10 учебным вопросам',
        expected_result='Прототип поиска', constraints='Только учебные примеры', users='Консультанты').model_dump()
    issues = rule_issues(fields)
    assert bool(issues) is expected
    assert all(i['kind'] == 'rule' for i in issues)


def test_live_review_validation_and_explicit_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv('MOCK', '0')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-not-a-real-key')
    monkeypatch.setenv('FALLBACK_TO_MOCK', '1')
    monkeypatch.setenv('LLM_LOG_PATH', str(tmp_path / 'calls.jsonl'))
    output = ReviewResult(issues=[])
    def parse(**kwargs):
        assert kwargs['store'] is False
        assert kwargs['text_format'] is ReviewResult
        return SimpleNamespace(output_parsed=output)
    class Client:
        def __init__(self, **kwargs):
            self.responses = SimpleNamespace(parse=parse)
        def __enter__(self): return self
        def __exit__(self, *args): pass
    import openai
    monkeypatch.setattr(openai, 'OpenAI', Client)
    reviewer = CardReviewer(Extractor())
    fields = CardContent(data='Available CSV').model_dump()
    assert reviewer.review(fields)['mode'] == 'live'
    output = ReviewResult(issues=[dict(field='data', quote='invented', message='x', question='x?')])
    assert reviewer.review(fields)['mode'] == 'mock'
    monkeypatch.setenv('FALLBACK_TO_MOCK', '0')
    with pytest.raises(RuntimeError): reviewer.review(fields)
    assert 'Available CSV' not in (tmp_path / 'calls.jsonl').read_text()
    monkeypatch.setenv('MAX_CALLS_PER_HOUR', '0')
    with pytest.raises(RuntimeError): reviewer.review(fields)


def test_forecast_uses_global_order_ties_and_independent_gains():
    a = dict(id='a', revision=1, first_published_at='2026-01-01', rating=dict(total=40, missing_fields=['data','users']))
    b = dict(id='b', revision=1, first_published_at='2026-01-01', rating=dict(total=60, missing_fields=[]))
    c = dict(id='c', revision=1, first_published_at='2026-01-02', rating=dict(total=50, missing_fields=[]))
    insights = catalog_insights(a, [b, c, a])
    assert insights['rank'] == 3 and insights['total'] == 3
    assert [(v['score_after'], v['rank_after']) for v in insights['actions']] == [(60, 1), (50, 2)]
    assert a['rating']['total'] == 40
