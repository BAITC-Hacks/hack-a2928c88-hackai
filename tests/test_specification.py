import io
import json
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from app.main import create_app
from app.specification import SpecContent, SpecGenerator, template_spec
from app.store import Store

B = {'X-Demo-Role':'business'}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('MOCK','1')
    with TestClient(create_app(tmp_path/'spec.db', seed_demo=False)) as client:
        yield client


def card(client):
    draft=client.post('/api/drafts',headers=B,json={'text':'Нужна форма заявок студентов','industry':'Образование'}).json()
    questions=client.post(f"/api/drafts/{draft['id']}/clarify",headers=B).json()['questions']
    record=client.post(f"/api/drafts/{draft['id']}/card",headers=B,json={'answers':{q['id']:'Учебные данные и согласованный результат' for q in questions}}).json()
    return change(client,record,'/confirm',{'fields':[k for k in ['title','need','context','users','data','constraints','expected_result','success_criteria'] if record.get(k)]}).json()


def change(client,record,suffix,body=None,method='post'):
    return getattr(client,method)(f"/api/cards/{record['id']}"+suffix,headers={**B,'If-Match':str(record['revision'])},json=body)


def generated(client):
    record=card(client)
    record=change(client,record,'/specification/settings',{'enabled':True},'patch').json()
    response=change(client,record,'/specification/generate')
    assert response.status_code==200,response.text
    return response.json()


def save_choice(client,record,selected=True):
    content=record['content']
    content['ideas'][0]['title']='ВЫБРАННАЯ ИДЕЯ'
    content['ideas'][1]['title']='ОТКЛОНЁННАЯ СЕКРЕТНАЯ ИДЕЯ'
    content['requirements']='Проверенное бизнесом требование <script>не выполнять</script>'
    r=change(client,record,'/specification/draft',{'content':content,'selected_idea_ids':[content['ideas'][0]['id']] if selected else []},'put')
    assert r.status_code==200,r.text
    return r.json()


def test_default_off_publishes_without_spec(client):
    record=card(client)
    assert not record['specification']['enabled']
    result=change(client,record,'/publish')
    assert result.status_code==200
    assert client.get('/api/cards').json()[0]['technical_specification'] is None
    assert client.get(f"/api/cards/{record['id']}/specification.pdf").status_code==404


def test_approval_and_publication_gate_selected_only(client):
    record=generated(client)
    assert record['selected_idea_ids']==[] and record['mode']=='mock'
    assert change(client,record,'/publish').status_code==422
    assert client.get(f"/api/cards/{record['id']}/specification").status_code==404
    assert client.get(f"/api/cards/{record['id']}/specification/draft").status_code==403
    assert client.get(f"/api/cards/{record['id']}/specification/draft.pdf").status_code==403
    record=save_choice(client,record)
    approved=change(client,record,'/specification/approve').json()
    assert approved['status']=='approved'
    assert client.get(f"/api/cards/{record['id']}/specification").status_code==404
    assert change(client,approved,'/publish').status_code==200
    public=client.get(f"/api/cards/{record['id']}/specification").json()
    assert len(public['ideas'])==1 and public['ideas'][0]['title']=='ВЫБРАННАЯ ИДЕЯ'
    assert public['requirements']==record['content']['requirements']
    assert 'ОТКЛОНЁННАЯ' not in json.dumps(client.get('/api/cards').json(),ensure_ascii=False)
    assert 'ОТКЛОНЁННАЯ' not in json.dumps(client.get(f"/api/cards/{record['id']}").json(),ensure_ascii=False)


def test_pdf_cyrillic_selected_only_and_literal_markup(client):
    record=save_choice(client,generated(client))
    draft=client.get(f"/api/cards/{record['id']}/specification/draft.pdf",headers=B)
    assert draft.status_code==200 and draft.content.startswith(b'%PDF')
    text='\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(draft.content)).pages)
    assert 'ЧЕРНОВИК' in text and 'ВЫБРАННАЯ ИДЕЯ' in text
    assert 'ОТКЛОНЁННАЯ' not in text and '<script>' in text
    record=change(client,record,'/specification/approve').json()
    change(client,record,'/publish')
    pdf=client.get(f"/api/cards/{record['id']}/specification.pdf")
    assert pdf.headers['content-type']=='application/pdf'
    text='\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert 'Утверждено бизнесом' in text and 'ЧЕРНОВИК' not in text


def test_edit_revokes_approval_preserves_published_snapshot(client):
    record=save_choice(client,generated(client))
    record=change(client,record,'/specification/approve').json()
    pub=change(client,record,'/publish').json()
    draft=client.get(f"/api/cards/{record['id']}/specification/draft",headers=B).json()
    old=client.get(f"/api/cards/{record['id']}/specification").json()
    draft['content']['summary']='Новый неутверждённый текст'
    changed=change(client,draft,'/specification/draft',{'content':draft['content'],'selected_idea_ids':[]},'put').json()
    assert changed['status']=='draft' and changed['approved_at'] is None
    assert change(client,changed,'/publish').status_code==422
    assert client.get(f"/api/cards/{record['id']}/specification").json()==old
    approved=change(client,changed,'/specification/approve').json()
    assert change(client,approved,'/publish').status_code==200
    assert client.get(f"/api/cards/{record['id']}/specification").json()['ideas']==[]


def test_card_change_requires_regeneration(client):
    record=generated(client)
    approved=change(client,record,'/specification/approve').json()
    modified=change(client,approved,'',{'changes':{'need':'Теперь нужна другая задача'}},'patch').json()
    assert modified['specification']['status']=='stale'
    assert change(client,modified,'/specification/approve').status_code==409
    assert change(client,modified,'/specification/generate').status_code==422
    modified=change(client,modified,'/confirm',{'fields':['need']}).json()
    assert change(client,modified,'/publish').status_code==422
    rebuilt=change(client,modified,'/specification/generate').json()
    assert rebuilt['source']['need']=='Теперь нужна другая задача' and rebuilt['selected_idea_ids']==[]


def test_disable_removes_spec_only_on_republication(client):
    record=change(client,generated(client),'/specification/approve').json()
    record=change(client,record,'/publish').json()
    disabled=change(client,record,'/specification/settings',{'enabled':False},'patch').json()
    assert client.get(f"/api/cards/{record['id']}/specification.pdf").status_code==200
    assert change(client,disabled,'/publish').status_code==200
    assert client.get(f"/api/cards/{record['id']}/specification.pdf").status_code==404
    current=client.get(f"/api/cards/{record['id']}").json()
    enabled=change(client,current,'/specification/settings',{'enabled':True},'patch').json()
    assert enabled['status']=='draft'


def test_versions_roles_and_invalid_choices(client):
    record=generated(client)
    body={'content':record['content'],'selected_idea_ids':['not-an-idea']}
    assert change(client,record,'/specification/draft',body,'put').status_code==422
    assert client.post(f"/api/cards/{record['id']}/specification/approve",headers={'X-Demo-Role':'team','If-Match':str(record['revision'])}).status_code==403
    assert client.post(f"/api/cards/{record['id']}/specification/approve",headers=B).status_code==428
    approved=change(client,record,'/specification/approve').json()
    assert change(client,record,'/specification/approve').status_code==409


def test_ai_failure_keeps_existing_draft(client, monkeypatch):
    record=generated(client)
    monkeypatch.setenv('MOCK','0'); monkeypatch.setenv('FALLBACK_TO_MOCK','0')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False); monkeypatch.delenv('NVIDIA_API_KEY',raising=False)
    assert change(client,record,'/specification/generate').status_code==503
    unchanged=client.get(f"/api/cards/{record['id']}/specification/draft",headers=B).json()
    assert unchanged==record


def test_generation_does_not_overwrite_concurrent_edit(tmp_path,monkeypatch):
    monkeypatch.setenv('MOCK','1')
    class Concurrent:
        def generate(self,source):
            with app.state.store.transaction() as db:
                record=Store.all(db,'card')[0]; record['revision']+=1
                Store.put(db,'card',record['card']['id'],record)
            return template_spec(source),'mock','template',[]
    app=create_app(tmp_path/'race.db',seed_demo=False,spec_generator=Concurrent())
    with TestClient(app) as c:
        record=card(c)
        record=change(c,record,'/specification/settings',{'enabled':True},'patch').json()
        assert change(c,record,'/specification/generate').status_code==409
        assert c.get(f"/api/cards/{record['id']}/specification/draft",headers=B).json()['content'] is None


@pytest.mark.parametrize('model', [None, 'gpt-4.1-mini'])
def test_openai_structured_generation_contract(monkeypatch, tmp_path, model):
    import openai
    monkeypatch.setenv('MOCK','0'); monkeypatch.setenv('OPENAI_API_KEY','test-key')
    monkeypatch.setenv('LLM_LOG_PATH', str(tmp_path / 'spec-calls.jsonl'))
    monkeypatch.delenv('OPENAI_REASONING_EFFORT', raising=False)
    if model is None:
        monkeypatch.delenv('OPENAI_MODEL', raising=False)
    else:
        monkeypatch.setenv('OPENAI_MODEL', model)
    received={}
    source={'title':'Учебная задача','need':'Собрать заявки'}
    class FakeClient:
        def __init__(self,**kwargs): self.responses=self
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def parse(self,**kwargs):
            received.update(kwargs)
            return SimpleNamespace(output_parsed=template_spec(source))
    monkeypatch.setattr(openai,'OpenAI',FakeClient)
    calls=[]
    result,mode,provider,_=SpecGenerator(lambda:calls.append(1)).generate(source)
    assert mode=='live' and provider=='openai' and calls==[1]
    assert received['store'] is False and received['text_format'] is SpecContent
    assert json.loads(received['input'])=={'source':source}
    assert received['model'] == (model or 'gpt-5.5') and received['max_output_tokens'] == 9000
    if model:
        assert 'reasoning' not in received
    else:
        assert received['reasoning'] == {'effort': 'low'}
    event = json.loads((tmp_path / 'spec-calls.jsonl').read_text())
    assert event['model'] == (model or 'gpt-5.5') and event['provider'] == 'openai'


@pytest.mark.parametrize('budget,valid_repair', [(100, True), (2, True), (100, False)])
def test_nvidia_specification_fallback_schema_repair_and_budget(monkeypatch, tmp_path, budget, valid_repair):
    from copy import deepcopy
    import openai
    from app.ai_config import NVIDIA_BASE_URL
    from app.llm import Extractor

    monkeypatch.setenv('MOCK', '0')
    monkeypatch.setenv('OPENAI_API_KEY', 'openai-test-key')
    monkeypatch.setenv('NVIDIA_API_KEY', 'nvidia-test-key')
    monkeypatch.delenv('NVIDIA_MODEL', raising=False)
    monkeypatch.setenv('FALLBACK_TO_MOCK', '1')
    monkeypatch.setenv('MAX_CALLS_PER_HOUR', str(budget))
    monkeypatch.setenv('LLM_LOG_PATH', str(tmp_path / 'spec-calls.jsonl'))
    source = {'title': 'Synthetic task', 'need': 'A simple application form'}
    requests = []
    settings = []

    class FakeClient:
        def __init__(self, **kwargs):
            settings.append(kwargs)
            self.responses = self
            self.chat = SimpleNamespace(completions=self)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def parse(self, **kwargs): raise OSError('unavailable')
        def create(self, **kwargs):
            requests.append(deepcopy(kwargs))
            content = template_spec(source).model_dump_json() if len(requests) == 2 and valid_repair else '{"title":"incomplete"}'
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    monkeypatch.setattr(openai, 'OpenAI', FakeClient)
    quota = Extractor()
    result, mode, provider, failures = SpecGenerator(quota.reserve).generate(source)
    assert failures[0] == 'openai:OSError'
    assert settings[1]['base_url'] == NVIDIA_BASE_URL
    assert all(r['model'] == 'meta/llama-3.3-70b-instruct' for r in requests)
    assert [m['role'] for m in requests[0]['messages']] == ['system', 'user']
    if budget == 2:
        assert len(requests) == 1 and len(quota.calls) == 2
    else:
        assert len(requests) == 2 and len(quota.calls) == 3
        assert [m['role'] for m in requests[1]['messages']] == ['system', 'user', 'assistant', 'user']
    if budget > 2 and valid_repair:
        assert mode == 'live' and provider == 'nvidia' and failures == ['openai:OSError']
    else:
        assert mode == 'mock' and provider == 'template' and len(failures) == 2
    assert isinstance(result, SpecContent)
    log = (tmp_path / 'spec-calls.jsonl').read_text()
    assert 'nvidia-test-key' not in log and source['need'] not in log


def test_template_handles_maximum_source():
    result=template_spec({'title':'Тест','need':'н'*15000,'expected_result':'р'*15000})
    assert result.summary and 'Полный текст' in result.summary


def test_restoring_source_does_not_restore_old_approval(client):
    record=generated(client)
    original=record['source']['need']
    record=change(client,record,'/specification/approve').json()
    record=change(client,record,'',{'changes':{'need':'Другая задача'}},'patch').json()
    record=change(client,record,'',{'changes':{'need':original}},'patch').json()
    assert record['specification']['stale']
    assert change(client,record,'/specification/approve').status_code==409


def test_pdf_rejects_revision_mismatch(client):
    record=generated(client)
    assert client.get(f"/api/cards/{record['id']}/specification/draft.pdf",headers={**B,'If-Match':str(record['revision']-1)}).status_code==409


def test_pdf_long_sections_paginate():
    from app.spec_pdf import specification_pdf
    source={'title':'Большое учебное ТЗ','need':'Потребность '*1000}
    content=template_spec(source).model_dump()
    content['requirements']='Проверяемый результат. '*350
    data=specification_pdf({**content,'source':source,'mode':'mock','provider':'template'},draft=True)
    pages=PdfReader(io.BytesIO(data)).pages
    assert len(pages)>3
    assert 'Проверяемый результат.' in '\n'.join(p.extract_text() for p in pages)


def test_spec_edits_preserve_current_card_review(client):
    record=card(client)
    record=change(client,record,'/review').json()
    assert record['review']['status']=='complete'
    record=change(client,record,'/specification/settings',{'enabled':True},'patch').json()
    record=change(client,record,'/specification/generate').json()
    record=save_choice(client,record)
    record=change(client,record,'/specification/approve').json()
    current=client.get(f"/api/cards/{record['id']}").json()
    assert current['review']['status']=='complete'
    assert current['review']['revision']==record['revision']
