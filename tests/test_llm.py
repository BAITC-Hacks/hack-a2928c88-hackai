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


def test_live_openai_parsed_and_invalid_quote_fallback(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import openai
    monkeypatch.setenv('MOCK', '0')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-not-a-real-key')
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    monkeypatch.setenv('FALLBACK_TO_MOCK', '1')
    monkeypatch.setenv('LLM_LOG_PATH', str(tmp_path / 'calls.jsonl'))
    captured = {}
    output = mock_extract({'draft':'Need a tool'}, {})
    class FakeClient:
        def __init__(self, **kwargs):
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
    output.evidence[0].quote = 'Invented revenue'
    result, mode, provider, failures = ai.extract({'draft':'Need a tool'}, {})
    assert mode == provider == 'mock' and failures[0] == 'openai:ValueError'
    assert all(e.quote in 'Need a tool' for e in result.evidence)
    log = (tmp_path / 'calls.jsonl').read_text()
    assert 'test-not-a-real-key' not in log and 'Need a tool' not in log
