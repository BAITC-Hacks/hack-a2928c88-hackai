import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.question_suggestion import FieldSelection, QuestionSuggester


def test_mock_is_explicit_and_answer_is_verbatim(monkeypatch, tmp_path):
    monkeypatch.setenv('MOCK', '1')
    monkeypatch.setenv('LLM_LOG_PATH', str(tmp_path / 'calls.jsonl'))
    def no_network():
        pytest.fail('Offline mode must not reserve an AI call')
    result = QuestionSuggester(no_network)({'text': 'Какие данные получит команда?'}, {'text': '  Наш ответ\nбез изменений.  '}, {})
    assert result == {'field': 'data', 'text': '  Наш ответ\nбез изменений.  ', 'mode': 'mock', 'provider': 'deterministic-template'}


def test_no_keys_and_fallback_disabled_fails_without_leaking_input(monkeypatch, tmp_path):
    monkeypatch.setenv('MOCK', '0')
    monkeypatch.setenv('FALLBACK_TO_MOCK', '0')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    logfile = tmp_path / 'calls.jsonl'
    monkeypatch.setenv('LLM_LOG_PATH', str(logfile))
    with pytest.raises(HTTPException) as exc:
        QuestionSuggester(lambda: None)({'text': 'private question'}, {'text': 'private answer'}, {})
    assert exc.value.status_code == 503
    assert 'private' not in logfile.read_text()
    assert json.loads(logfile.read_text())['mode'] == 'unavailable'


def test_live_schema_only_selects_field_and_cannot_rewrite_answer(monkeypatch, tmp_path):
    import openai
    monkeypatch.setenv('MOCK', '0')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('LLM_LOG_PATH', str(tmp_path / 'calls.jsonl'))
    calls = []
    def parse(**kwargs):
        assert kwargs['text_format'] is FieldSelection and kwargs['store'] is False
        assert 'private card data' not in kwargs['input']
        return SimpleNamespace(output_parsed=FieldSelection(field='constraints'))
    class Client:
        def __init__(self, **kwargs):
            self.responses = SimpleNamespace(parse=parse)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    monkeypatch.setattr(openai, 'OpenAI', Client)
    result = QuestionSuggester(lambda: calls.append('reserve'))({'text': 'Срок проекта?'}, {'text': 'Только согласованный срок.'}, {'private': 'private card data'})
    assert calls == ['reserve']
    assert result == {'field': 'constraints', 'text': 'Только согласованный срок.', 'mode': 'live', 'provider': 'openai'}
