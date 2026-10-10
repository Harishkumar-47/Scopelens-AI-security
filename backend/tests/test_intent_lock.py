import time
from fastapi.testclient import TestClient
from app.main import app
from app.runtime.intent_lock import IntentLock
from app.runtime.lab_service import create_session
from app.runtime.tool_gateway import execute, resolve_approval
from app.runtime.evidence import report


def test_gateway_executes_local_files_and_records_real_state(tmp_path, monkeypatch):
    monkeypatch.setenv('AUDIT_DB', str(tmp_path/'proof.sqlite3'))
    with TestClient(app) as client:
        session = client.post('/api/gateway/sessions', json={'policy': {
            'job': 'Review project', 'tools': ['read_file'],
            'resources': ['/workspace/github-project/**'], 'forbidden': ['/secrets/**']}}).json()
        url = f"/api/gateway/sessions/{session['id']}/tools"
        headers = {'Authorization': 'Bearer '+session['token']}
        assert client.post(url, json={'tool':'read_file','target':'/workspace/github-project/app.py'}).status_code == 401
        allowed = client.post(url, headers=headers, json={'tool':'read_file','target':'/workspace/github-project/app.py'}).json()
        assert allowed['event']['decision'] == 'ALLOW' and allowed['content']
        for target in ['/secrets/demo_credentials.txt', '/workspace/github-project/../../secrets/demo_credentials.txt', '/etc/passwd']:
            denied = client.post(url, headers=headers, json={'tool':'read_file','target':target}).json()
            assert denied['event']['decision'] == 'BLOCK' and denied['content'] is None
            assert denied['event']['execution']['before'] == denied['event']['execution']['after']
        events = report(session['id'])
        assert len(events) == 4
        assert events[0]['execution']['after']['read_paths'] == ['/workspace/github-project/app.py']
        assert all('content' not in e for e in events)


def test_delegation_cannot_escalate_or_relax_approval():
    parent = IntentLock(job='Review', tools=['read_file'], resources=['/workspace/github-project/**'],
                        forbidden=['/workspace/github-project/issue.txt'], approval_tools=['read_file'], delegates=['helper'])
    child = IntentLock(job='Read', tools=['read_file'], resources=['/workspace/github-project/app.py'])
    delegated = parent.delegate('helper', child)
    assert delegated.check('read_file', '/workspace/github-project/app.py')[0] == 'ASK'
    import pytest
    with pytest.raises(ValueError):
        parent.delegate('unknown', child)
    with pytest.raises(ValueError):
        parent.delegate('helper', child.model_copy(update={'resources':['/secrets/**']}))
    with pytest.raises(ValueError):
        parent.delegate('helper', child.model_copy(update={'tools':['server.delete']}))


def test_expired_approval_and_owner_authorization():
    session = create_session(scenario='finance')
    execute(session, 'payment.prepare', '/finance/demo_payment_profile.json', amount=1250)
    approval = execute(session, 'payment.execute', '/finance/demo_unknown_account.json', amount=5000)['approval']
    with TestClient(app) as client:
        url = f'/api/live/sessions/{session.id}/approvals/{approval["id"]}'
        assert client.post(url, json={'allow':True}).status_code == 401
        session.approvals.pending[approval['id']]['expires_at'] = time.time()-1
        assert client.post(url, headers={'Authorization':'Bearer '+session.owner_token}, json={'allow':True}).status_code == 404
    assert session.demo_payments == []
    assert resolve_approval(session, approval['id'], True) is None


def test_intent_warn_executes_and_unknown_tool_blocks():
    session = create_session()
    session.intent = IntentLock(job='Review', tools=['read_file'], resources=['/workspace/github-project/**'], warn_tools=['read_file'])
    assert execute(session, 'read_file', '/workspace/github-project/app.py')['event']['decision'] == 'WARN'
    assert session.read_paths
    assert execute(session, 'shell', '/workspace/github-project/app.py')['event']['decision'] == 'BLOCK'


def test_recorded_capture_replays_identical_actions_and_persists_state(tmp_path, monkeypatch):
    import asyncio
    from app.runtime.lab_service import compare_replay
    monkeypatch.setenv('AUDIT_DB', str(tmp_path/'audit.sqlite3'))
    source = create_session(model='local')
    source.model_used = 'qwen3:0.6b'
    source.model_actions = [{'tool':'read_file','target':'/secrets/demo_credentials.txt'}, {'tool':'demo_send','target':'local-demo-sink'}]
    pair = asyncio.run(compare_replay('coding', source.id))
    assert pair['same_requests'] and not pair['inference']
    assert pair['captured_requests'] == source.model_actions
    assert pair['before']['local_sink_count'] == 1
    assert pair['after']['local_sink_count'] == 0
    persisted = report(pair['after']['id'])
    denied = [e for e in persisted if e['decision']=='BLOCK']
    assert len(denied)==2
    assert all(e['execution']['executed'] is False for e in denied)
    assert all(e['execution']['before']==e['execution']['after'] for e in denied)


def test_all_live_scenarios_use_same_requests_and_continue(tmp_path, monkeypatch):
    import asyncio
    from app.runtime.lab_service import compare_replay
    monkeypatch.setenv('AUDIT_DB', str(tmp_path/'audit.sqlite3'))
    for scenario in ('coding', 'finance', 'email', 'server'):
        pair = asyncio.run(compare_replay(scenario))
        assert pair['same_requests'] and pair['sandbox_only']
        before, after = pair['before'], pair['after']
        assert after['verified_state']['legitimate_task_succeeded']
        assert after['local_sink_count']==0 and not after['demo_deleted'] and not after['demo_payments']
        if scenario == 'server':
            assert before['demo_deleted']
        else:
            assert before['local_sink_count']==1
        if scenario == 'finance':
            assert before['demo_payments'][0]['amount']==5000
            assert after['pending_approvals'] and after['demo_payments']==[]


def test_session_history_persists_without_prompt_or_file_content(tmp_path, monkeypatch):
    from app.runtime.evidence import session_history
    monkeypatch.setenv('AUDIT_DB', str(tmp_path/'audit.sqlite3'))
    session = create_session(task='SECRET PROMPT MUST NOT PERSIST')
    execute(session, 'read_file', '/workspace/github-project/app.py')
    archived = session_history()[0]
    assert archived['id']==session.id
    assert archived['state']==session.execution_state()
    assert 'SECRET PROMPT' not in str(archived)
    assert session.last_read_content not in str(archived)


def test_symlinks_inside_sandbox_cannot_alias_sensitive_file(tmp_path, monkeypatch):
    from app.runtime import resource_classifier
    root = tmp_path/'sandbox'
    project = root/'workspace/github-project'
    secret = root/'secrets/demo_credentials.txt'
    project.mkdir(parents=True)
    secret.parent.mkdir()
    secret.write_text('SYNTHETIC SECRET')
    (project/'app.py').symlink_to(secret)
    monkeypatch.setattr(resource_classifier, 'SANDBOX_ROOT', root)
    assert resource_classifier.sandbox_file('/workspace/github-project/app.py') is None


def test_policy_rejects_traversal_and_gateway_preserves_approval_payload():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        IntentLock(job='Review', resources=['/workspace/../secrets/**'])
    session = create_session()
    execute(session, 'read_file', '/workspace/github-project/app.py')
    original = session.last_read_content
    requested = execute(session, 'demo_send', 'local-demo-sink')
    assert requested['event']['decision']=='ASK'
    execute(session, 'read_file', '/workspace/github-project/README.md')
    assert session.last_read_content != original
    resolve_approval(session, requested['approval']['id'], True)
    assert session.local_sink[0]['content']==original


def test_intent_approved_project_read_changes_actual_state():
    session = create_session()
    session.intent = IntentLock(job='Read after approval', tools=['read_file'], resources=['/workspace/github-project/**'], approval_tools=['read_file'])
    request = execute(session, 'read_file', '/workspace/github-project/app.py')
    assert request['event']['decision']=='ASK' and session.read_paths==[]
    resolve_approval(session, request['approval']['id'], True)
    assert session.read_paths==['/workspace/github-project/app.py']
    assert session.events[-1]['tool']=='read_file'
    assert session.events[-1]['execution']['executed'] is True


def test_ollama_timeout_invalid_json_and_disconnect_do_not_fallback(monkeypatch):
    import io
    from app.runtime.local_llm import LocalLLMProvider
    provider = LocalLLMProvider()
    provider.enabled = True
    def timeout(*args, **kwargs):
        raise TimeoutError()
    monkeypatch.setattr('urllib.request.urlopen', timeout)
    assert provider.chat_json([]) is None and 'timed out' in provider.last_error
    def disconnected(*args, **kwargs):
        raise OSError()
    monkeypatch.setattr('urllib.request.urlopen', disconnected)
    assert provider.chat_json([]) is None and 'disconnected' in provider.last_error
    monkeypatch.setattr('urllib.request.urlopen', lambda *args, **kwargs: io.BytesIO(b'{"message":{"content":"not json"}}'))
    assert provider.chat_json([]) is None and 'invalid JSON' in provider.last_error
