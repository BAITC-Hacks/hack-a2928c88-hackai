import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.llm import Extractor
from app.review import CardReviewer
from app.schemas import CardContent

B = {'X-Demo-Role':'business'}


def fake_nvidia(monkeypatch, tmp_path, outputs):
    import openai
    monkeypatch.setenv('MOCK', '0')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-openai')
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-nvidia')
    monkeypatch.setenv('NVIDIA_MODEL', 'meta/llama-3.3-70b-instruct')
    monkeypatch.setenv('LLM_LOG_PATH', str(tmp_path / 'calls.jsonl'))
    calls = []
    class Client:
        def __init__(self, **kwargs):
            self.provider = 'nvidia' if 'base_url' in kwargs else 'openai'
            self.responses = SimpleNamespace(parse=self.parse)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def parse(self, **kwargs):
            calls.append(('openai', kwargs))
            raise RuntimeError('provider-internal-must-not-leak')
        def create(self, **kwargs):
            calls.append(('nvidia', {**kwargs, 'messages':list(kwargs['messages'])}))
            item = outputs.pop(0)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(item)))])
    monkeypatch.setattr(openai, 'OpenAI', Client)
    return calls


def test_review_fallback_repairs_evidence_counts_budget_and_logs_safely(monkeypatch, tmp_path):
    invalid = dict(field='data', quote='invented', message='Possible gap', question='What data?')
    valid = {**invalid, 'quote':'Available CSV'}
    calls = fake_nvidia(monkeypatch, tmp_path, [{'issues':[invalid]}, {'issues':[valid]}])
    monkeypatch.setenv('FALLBACK_TO_MOCK', '0')
    budget = Extractor()
    result = CardReviewer(budget).review(CardContent(data='Available CSV').model_dump())
    assert result['provider'] == 'nvidia' and result['mode'] == 'live'
    assert result['model'] == 'meta/llama-3.3-70b-instruct'
    assert any(i['quote'] == 'Available CSV' and i['kind'] == 'ai' for i in result['issues'])
    assert [p for p, _ in calls] == ['openai','nvidia','nvidia']
    assert [m['role'] for m in calls[-1][1]['messages']] == ['system','user','assistant','user']
    assert len(budget.calls) == 3
    log = (tmp_path/'calls.jsonl').read_text()
    assert 'nvidia' in log and 'card-review' in log
    assert all(secret not in log for secret in ['test-openai','test-nvidia','Available CSV','provider-internal'])


def test_second_opinion_calls_only_nvidia_and_never_reads_first_opinion(monkeypatch, tmp_path):
    calls = fake_nvidia(monkeypatch, tmp_path, [{'issues':[]}])
    result = CardReviewer(Extractor()).review_nvidia(CardContent(need='Source input').model_dump())
    assert result['provider'] == 'nvidia'
    assert [p for p, _ in calls] == ['nvidia']
    payload = json.loads(calls[0][1]['messages'][1]['content'])
    assert set(payload) == set(CardContent.model_fields)


def test_second_opinion_unavailable_never_silently_falls_back(monkeypatch, tmp_path):
    calls = fake_nvidia(monkeypatch, tmp_path, [])
    monkeypatch.delenv('NVIDIA_API_KEY')
    monkeypatch.setenv('FALLBACK_TO_MOCK','1')
    with pytest.raises(RuntimeError):
        CardReviewer(Extractor()).review_nvidia(CardContent().model_dump())
    assert calls == []
    monkeypatch.setenv('NVIDIA_API_KEY','test-nvidia')
    monkeypatch.setenv('MAX_CALLS_PER_HOUR','0')
    with pytest.raises(RuntimeError):
        CardReviewer(Extractor()).review_nvidia(CardContent().model_dump())
    assert calls == []


def test_second_opinion_rejects_invented_evidence_after_one_retry(monkeypatch, tmp_path):
    bad = {'issues':[dict(field='data',quote='invented',message='x',question='x?')]}
    calls = fake_nvidia(monkeypatch, tmp_path, [bad,bad])
    with pytest.raises(RuntimeError):
        CardReviewer(Extractor()).review_nvidia(CardContent(data='Real CSV').model_dump())
    assert len(calls) == 2


def test_api_second_opinion_is_separate_versioned_and_read_only(monkeypatch, tmp_path):
    monkeypatch.setenv('MOCK','1')
    monkeypatch.setenv('LLM_LOG_PATH',str(tmp_path/'calls.jsonl'))
    with TestClient(create_app(tmp_path/'second.db', seed_demo=False)) as c:
        draft = c.post('/api/drafts',headers=B,json={'text':'Synthetic example','industry':'Education','synthetic':True}).json()
        c.post(f"/api/drafts/{draft['id']}/clarify",headers=B)
        card = c.post(f"/api/drafts/{draft['id']}/card",headers=B,json={'answers':{}}).json()
        path = f"/api/cards/{card['id']}"
        def action(suffix, body=None, method='post'):
            return getattr(c,method)(path+suffix,headers={**B,'If-Match':str(card['revision'])},json=body)
        assert c.post(path+'/review/nvidia').status_code == 403
        assert c.post(path+'/review/nvidia',headers=B).status_code == 428
        card = action('/review').json()
        original = card
        checked = action('/review/nvidia').json()
        assert checked['nvidia_review']['mode'] == 'mock'
        assert {k:v for k,v in checked.items() if k != 'nvidia_review'} == {k:v for k,v in original.items() if k != 'nvidia_review'}
        card = action('/confirm',{'fields':['need','title']}).json()
        assert card['review']['status'] == card['nvidia_review']['status'] == 'complete'
        card = action('/publish').json()
        public = c.get('/api/cards').json()[0]
        assert public['nvidia_review'] == card['nvidia_review']
        # Toggling specification only changes revision, not the reviewed source.
        result = action('/specification/settings',{'enabled':True},'patch').json()
        assert result['nvidia_review']['revision'] == result['revision']
        card = c.get(path).json()
        card = action('',{'changes':{'data':'New data'}},'patch').json()
        assert card['review']['status'] == card['nvidia_review']['status'] == 'stale'
        assert c.get('/api/cards').json()[0]['nvidia_review'] == public['nvidia_review']
        # Real mode without the requested provider preserves the old result and inputs.
        monkeypatch.setenv('MOCK','0'); monkeypatch.delenv('NVIDIA_API_KEY',raising=False)
        failed = action('/review/nvidia')
        assert failed.status_code == 503 and 'NVIDIA_API_KEY' in failed.json()['detail']
        assert c.get(path).json() == card


def test_second_opinion_rechecks_revision_after_model_returns(monkeypatch, tmp_path):
    monkeypatch.setenv('MOCK','1')
    class RacingReviewer:
        def review_nvidia(self, fields):
            changed = c.patch(path,headers={**B,'If-Match':str(card['revision'])},json={'changes':{'data':'Updated'}})
            assert changed.status_code == 200
            return dict(status='complete',mode='mock',provider='mock',issues=[])
    with TestClient(create_app(tmp_path/'race.db',seed_demo=True,reviewer=RacingReviewer())) as c:
        card = c.get('/api/cards').json()[0]; path = '/api/cards/'+card['id']
        card = c.get(path).json()
        result = c.post(path+'/review/nvidia',headers={**B,'If-Match':str(card['revision'])})
        assert result.status_code == 409
        assert c.get(path).json()['nvidia_review']['status'] == 'not_run'
