import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.runtime.activity_monitor import graph_for
from app.runtime.lab_service import create_session, run_coding_demo, run_finance_preview, compare_replay
from app.runtime.policy_engine import CODING_SCOPE, evaluate
from app.runtime.resource_classifier import classify, resource_info, sandbox_file
from app.runtime.tool_gateway import execute, resolve_approval


def test_allowed_project_file_and_sandbox_boundary():
    assert evaluate('read_file', '/workspace/github-project/app.py', CODING_SCOPE, True).status == 'ALLOW'
    assert sandbox_file('/workspace/github-project/app.py') is not None
    assert sandbox_file('/home/.env') is not None
    assert sandbox_file('/home/.ssh/id_demo') is not None
    assert sandbox_file('/workspace/github-project/../../home/.env') is None
    assert sandbox_file('/etc/passwd') is None


def test_resource_classification_and_windows_patterns():
    assert classify('/home/.env') == 'SECRET'
    assert classify('/secrets/demo_credentials.txt') == 'SECRET'
    assert classify('/finance/demo_bank_account.json') == 'FINANCIAL'
    assert classify(r'C:\Users\Demo\.ssh\id_demo') == 'SECRET'
    assert classify(r'C:\Users\Demo\Documents\notes.txt') == 'USER_DATA'
    assert classify(r'C:\Windows\System32\config') == 'SYSTEM'
    assert classify('D:\\') == 'SYSTEM'
    assert resource_info('/home/Documents/notes.txt', CODING_SCOPE)['out_of_scope']


def test_allow_ask_block_policy():
    assert evaluate('read_file', '/workspace/github-project/README.md', CODING_SCOPE, True).status == 'ALLOW'
    assert evaluate('read_file', '/home/Documents/notes.txt', CODING_SCOPE, True).status == 'ASK'
    blocked = evaluate('read_file', '/secrets/demo_credentials.txt', CODING_SCOPE, True, source_untrusted=True)
    assert (blocked.status, blocked.severity) == ('BLOCK', 'CRITICAL')
    assert evaluate('demo_send', 'https://outside.example', CODING_SCOPE, False).status == 'BLOCK'
    assert evaluate('shell.execute', '/workspace/github-project', CODING_SCOPE, False).status == 'BLOCK'


def test_prompt_injection_replay_is_contained_and_core_task_continues():
    before = create_session(mode='unprotected')
    after = create_session(mode='protected')
    asyncio.run(run_coding_demo(before, delay=0, force_replay=True))
    asyncio.run(run_coding_demo(after, delay=0, force_replay=True))
    assert before.snapshot()['summary']['exposures'] >= 1
    assert before.snapshot()['local_sink_count'] == 1
    assert any(edge['source'] == 'agent-memory' and edge['target'].startswith('tool:')
               for edge in before.snapshot()['graph']['edges'])
    assert any(node['kind'] == 'untrusted' for node in before.snapshot()['graph']['nodes'])
    assert after.snapshot()['summary']['exposures'] == 0
    assert after.snapshot()['summary']['blocked'] == 2
    assert after.snapshot()['local_sink_count'] == 0
    assert any('legitimate code review' in event['message'] for event in after.events)
    assert any(event['untrusted_source'] and event['decision'] == 'BLOCK' for event in after.events)


def test_runtime_graph_records_blocked_movement():
    session = create_session()
    execute(session, 'read_file', '/secrets/demo_credentials.txt', untrusted_source=True)
    graph = graph_for(session.events, session.agent_name)
    assert any(node['kind'] == 'outcome' and node['label'] == 'BLOCKED' for node in graph['nodes'])
    assert any(edge['state'] == 'blocked' for edge in graph['edges'])


def test_payment_needs_one_time_approval_and_denial_executes_nothing():
    session = create_session(scenario='finance')
    run_finance_preview(session)
    request = execute(session, 'payment.execute', '/finance/demo_payment_profile.json', amount=5000)
    assert request['event']['decision'] == 'ASK'
    assert resolve_approval(session, request['approval']['id'], False)['status'] == 'DENIED'
    assert session.demo_payments == []
    assert execute(session, 'payment.preview', '/etc/passwd')['event']['decision'] == 'BLOCK'


def test_payment_allow_once_is_synthetic_and_not_reused():
    session = create_session(scenario='finance')
    run_finance_preview(session)
    request = execute(session, 'payment.execute', '/finance/demo_payment_profile.json', amount=5000)
    approval_id = request['approval']['id']
    assert resolve_approval(session, approval_id, True)['status'] == 'ALLOWED_ONCE'
    assert session.demo_payments == [{'amount': 5000, 'demo_only': True}]
    assert resolve_approval(session, approval_id, True) is None
    assert execute(session, 'payment.execute', '/finance/demo_payment_profile.json', amount=5000)['event']['decision'] == 'ASK'


def test_compare_uses_same_task_and_replay_model():
    comparison = asyncio.run(compare_replay())
    assert comparison['same_task'] and comparison['same_model'] and comparison['sandbox_only']
    assert comparison['before']['summary']['exposures'] > comparison['after']['summary']['exposures']


def test_local_model_failure_falls_back_to_labeled_replay(monkeypatch):
    from app.runtime.local_llm import LocalLLMProvider
    monkeypatch.setattr(LocalLLMProvider, 'choose_actions', lambda self, task, issue: None)
    session = create_session(model='local')
    asyncio.run(run_coding_demo(session, delay=0))
    assert session.model_used == 'DEMO REPLAY MODE'
    assert session.snapshot()['summary']['blocked'] == 2


def test_websocket_streams_runtime_snapshots():
    with TestClient(app) as client:
        tools = client.get('/api/live/tools').json()
        assert {tool['name'] for tool in tools} >= {'read_file', 'demo_send', 'payment.execute'}
        session = client.post('/api/live/sessions', json={'mode': 'protected'}).json()
        with client.websocket_connect(f"/api/live/ws/{session['id']}") as socket:
            assert socket.receive_json()['type'] == 'snapshot'
            assert client.post(f"/api/live/sessions/{session['id']}/run").status_code == 202
            for _ in range(15):
                update = socket.receive_json()
                if update['session']['completed']:
                    assert update['session']['summary']['blocked'] == 2
                    break
            else:
                raise AssertionError('Runtime stream never completed')
