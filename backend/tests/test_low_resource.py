import io
import json
import pytest
from fastapi import HTTPException
from app.runtime.local_llm import LocalLLMProvider, _INFERENCE_LOCK
from app.runtime.practical_lab import _valid_actions


def test_status_polling_never_loads_model(monkeypatch):
    monkeypatch.setenv('LLM_ENABLED', 'true')
    monkeypatch.setenv('LLM_BASE_URL', 'http://localhost:11434')
    monkeypatch.delenv('LOCAL_LLM_MODEL', raising=False)
    urls = []
    def respond(url, **kwargs):
        urls.append(url)
        return io.BytesIO(b'{"models":[{"name":"qwen3:0.6b"}]}')
    monkeypatch.setattr('urllib.request.urlopen', respond)
    assert LocalLLMProvider().status()['ready']
    assert urls == ['http://localhost:11434/api/tags']


def test_cpu_budget_and_concurrent_request_rejection(monkeypatch):
    monkeypatch.setenv('LLM_ENABLED', 'true')
    provider = LocalLLMProvider()
    def respond(request, **kwargs):
        body = json.loads(request.data)
        assert body['keep_alive'] == '60s'
        assert body['options']['num_ctx'] == 2048
        assert body['options']['num_gpu'] == 0
        assert body['options']['num_predict'] == 256
        competing = LocalLLMProvider()
        assert competing.chat_json([]) is None
        assert 'busy' in competing.last_error
        return io.BytesIO(b'{"message":{"content":"{\\"reply\\":\\"Hello\\"}"}}')
    monkeypatch.setattr('urllib.request.urlopen', respond)
    assert provider.chat_json([]) == {'reply': 'Hello'}
    assert not _INFERENCE_LOCK.locked()


@pytest.mark.parametrize('actions', [None, [{'tool': 'shell'}], [{'tool': 'finish', 'target': '/etc/passwd'}], [{'tool':'finish'}]*4])
def test_practical_rejects_entire_invalid_plan(actions):
    with pytest.raises(HTTPException) as error:
        _valid_actions(actions)
    assert error.value.status_code == 502


def test_structured_action_schema_is_sent_to_ollama(monkeypatch):
    from app.runtime.practical_lab import PLAN_SCHEMA
    monkeypatch.setenv('LLM_ENABLED', 'true')
    def respond(request, **kwargs):
        assert json.loads(request.data)['format'] == PLAN_SCHEMA
        return io.BytesIO(json.dumps({'message': {'content': json.dumps({'actions': [{'tool': 'finish'}]})}}).encode())
    monkeypatch.setattr('urllib.request.urlopen', respond)
    assert LocalLLMProvider().chat_json([], response_schema=PLAN_SCHEMA) == {'actions': [{'tool': 'finish'}]}


def test_discovery_does_not_recommend_unrelated_heavy_model(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr(LocalLLMProvider, 'installed_models', lambda self: ['other-project:70b'])
    result = TestClient(app).get('/api/tester/models').json()
    assert result['recommended_model'] == 'demo'
    assert result['models'][1]['id'] == 'other-project:70b'


def test_withheld_model_answer_is_error_not_synthetic_model_reply(monkeypatch):
    import asyncio
    from unittest.mock import patch
    from app.runtime.practical_lab import create, chat
    session = create('protected', 'qwen', '')
    with patch.object(LocalLLMProvider, 'chat_json', side_effect=[
            {'actions': [{'tool': 'finish'}]}, {'reply': 'DEMO-ACCOUNT-0001'}]):
        with pytest.raises(HTTPException) as error:
            asyncio.run(chat(session, 'Summarize the bill'))
    assert error.value.status_code == 502
    assert 'ScopeLens withheld' in error.value.detail
    assert all(message['role'] != 'assistant' for message in session.messages)
    assert session.trace[-1]['tool'] == 'output.filter'
    assert not session.busy
