import json
import pytest
from app.llm import Extractor, Extraction, validate_evidence, mock_extract


def test_invented_quote_and_duplicate_field_rejected():
    result = mock_extract({'draft':'A real input'}, {})
    result.evidence[0].quote = 'Invented fact'
    with pytest.raises(ValueError, match='R-QUOTE'):
        validate_evidence(result, {'draft':'A real input'})
    result = mock_extract({'draft':'A real input'}, {})
    result.evidence.append(result.evidence[0])
    with pytest.raises(ValueError, match='R-QUOTE'):
        validate_evidence(result, {'draft':'A real input'})


def test_missing_credentials_explicit_fallback(monkeypatch):
    monkeypatch.setenv('MOCK','0')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    monkeypatch.setenv('FALLBACK_TO_MOCK','1')
    result, mode, provider, failures = Extractor().extract({'draft':'Need a tool'}, {})
    assert mode == provider == 'mock' and len(failures) == 2
    monkeypatch.setenv('FALLBACK_TO_MOCK','0')
    with pytest.raises(RuntimeError):
        Extractor().extract({'draft':'Need a tool'}, {})


def test_ai_cannot_confirm_or_select():
    output = mock_extract({'draft':'Need a tool'}, {}).model_dump()
    output['confirmations'] = {'need':True}
    with pytest.raises(ValueError):
        Extraction.model_validate(output)


def test_budget_counts_calls_not_just_success(monkeypatch):
    monkeypatch.setenv('MAX_CALLS_PER_HOUR','1')
    ai = Extractor()
    ai.reserve()
    with pytest.raises(ValueError, match='hourly_budget'):
        ai.reserve()


@pytest.mark.parametrize('model, effort', [(None, None), ('gpt-4.1-mini', 'low'), ('gpt-5.5', 'medium')])
def test_live_openai_parsed_and_invalid_quote_fallback(monkeypatch, tmp_path, model, effort):
    from types import SimpleNamespace
    import openai
    monkeypatch.setenv('MOCK', '0')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-not-a-real-key')
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    monkeypatch.setenv('FALLBACK_TO_MOCK', '1')
    monkeypatch.setenv('LLM_LOG_PATH', str(tmp_path / 'calls.jsonl'))
    monkeypatch.delenv('AI_TIMEOUT_SECONDS', raising=False)
    for name, value in [('OPENAI_MODEL', model), ('OPENAI_REASONING_EFFORT', effort)]:
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    captured = {}
    settings = {}
    output = mock_extract({'draft':'Need a tool'}, {})
    class FakeClient:
        def __init__(self, **kwargs):
            settings.update(kwargs)
            self.responses = self
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def parse(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_parsed=output)
    monkeypatch.setattr(openai, 'OpenAI', FakeClient)
    ai = Extractor()
    _, mode, provider, failures = ai.extract({'draft':'Need a tool'}, {})
    assert mode == 'live' and provider == 'openai' and not failures
    assert captured['store'] is False and captured['text_format'] is Extraction
    assert captured['model'] == (model or 'gpt-5.5')
    assert captured['max_output_tokens'] == 6000 and settings['timeout'] == 45
    if model == 'gpt-4.1-mini':
        assert 'reasoning' not in captured
    else:
        assert captured['reasoning'] == {'effort': effort or 'low'}
    output.evidence[0].quote = 'Invented revenue'
    result, mode, provider, failures = ai.extract({'draft':'Need a tool'}, {})
    assert mode == provider == 'mock' and failures[0] == 'openai:ValueError'
    assert all(e.quote in 'Need a tool' for e in result.evidence)
    log = (tmp_path / 'calls.jsonl').read_text()
    assert 'test-not-a-real-key' not in log and 'Need a tool' not in log
    events = [json.loads(line) for line in log.splitlines()]
    assert events[0]['model'] == (model or 'gpt-5.5') and events[1]['model'] is None


@pytest.mark.parametrize('bad_quote,budget,valid_repair', [
    (False, 100, True), (True, 100, True), (True, 2, True), (False, 100, False),
])
def test_nvidia_fallback_repairs_once_with_budget_and_exact_quotes(monkeypatch, tmp_path, bad_quote, budget, valid_repair):
    from copy import deepcopy
    from types import SimpleNamespace
    import openai
    from app.ai_config import NVIDIA_BASE_URL

    monkeypatch.setenv('MOCK', '0')
    monkeypatch.setenv('OPENAI_API_KEY', 'openai-test-key')
    monkeypatch.setenv('NVIDIA_API_KEY', 'nvidia-test-key')
    monkeypatch.setenv('NVIDIA_MODEL', 'test-nvidia-model')
    monkeypatch.setenv('FALLBACK_TO_MOCK', '1')
    monkeypatch.setenv('MAX_CALLS_PER_HOUR', str(budget))
    monkeypatch.setenv('LLM_LOG_PATH', str(tmp_path / 'calls.jsonl'))
    source = {'draft': 'A real business need'}
    expected = mock_extract(source, {})
    altered = expected.model_copy(deep=True)
    altered.evidence[0].quote = 'Invented fact'
    malformed = altered.model_dump_json() if bad_quote else 'not json'
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
            content = expected.model_dump_json() if len(requests) == 2 and valid_repair else malformed
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    monkeypatch.setattr(openai, 'OpenAI', FakeClient)
    ai = Extractor()
    result, mode, provider, failures = ai.extract(source, {})
    assert failures[0] == 'openai:OSError'
    assert settings[1]['base_url'] == NVIDIA_BASE_URL
    assert all(r['model'] == 'test-nvidia-model' for r in requests)
    assert 'reasoning' not in requests[0]
    assert [m['role'] for m in requests[0]['messages']] == ['system', 'user']
    if budget == 2:
        assert len(requests) == 1 and len(ai.calls) == 2
    else:
        assert len(requests) == 2 and len(ai.calls) == 3
        assert [m['role'] for m in requests[1]['messages']] == ['system', 'user', 'assistant', 'user']
        assert requests[1]['messages'][2]['content'] == malformed
    if budget > 2 and valid_repair:
        assert mode == 'live' and provider == 'nvidia'
        assert failures == ['openai:OSError']
    else:
        assert mode == provider == 'mock' and len(failures) == 2
    assert all(item.quote in source[item.source_id] for item in result.evidence)
    log = (tmp_path / 'calls.jsonl').read_text()
    assert 'nvidia-test-key' not in log and source['draft'] not in log
