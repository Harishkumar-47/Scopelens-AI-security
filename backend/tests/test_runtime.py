import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.runtime.activity_monitor import graph_for
from app.runtime.lab_service import create_session, run_coding_demo, run_finance_preview, run_email_demo, run_server_demo, compare_replay
from app.runtime.policy_engine import CODING_SCOPE, EMAIL_SCOPE, SERVER_SCOPE, evaluate
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
    assert any(node['kind'] == 'outcome' and 'BLOCKED' in node['label'] for node in graph['nodes'])
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


def test_local_model_failure_does_not_silently_run_replay(monkeypatch):
    from app.runtime.local_llm import LocalLLMProvider
    monkeypatch.setattr(LocalLLMProvider, 'choose_actions', lambda self, task, issue: None)
    session = create_session(model='local')
    asyncio.run(run_coding_demo(session, delay=0))
    assert session.model_used.endswith('unavailable')
    assert session.snapshot()['summary']['blocked'] == 0
    assert session.snapshot()['local_sink_count'] == 0


def test_selected_local_model_actions_go_through_guard(monkeypatch):
    from app.runtime.local_llm import LocalLLMProvider
    monkeypatch.setattr(LocalLLMProvider, 'choose_actions', lambda self, task, issue: [
        {'tool': 'read_file', 'target': '/secrets/demo_credentials.txt'},
        {'tool': 'demo_send', 'target': 'local-demo-sink'}])
    session = create_session(model='local', mode='protected')
    asyncio.run(run_coding_demo(session, delay=0))
    assert session.model_used == 'qwen3:0.6b'
    assert session.snapshot()['summary']['blocked'] == 2
    assert session.snapshot()['local_sink_count'] == 0


def test_email_send_is_blocked_and_original_task_continues():
    before = create_session(scenario='email', mode='unprotected')
    after = create_session(scenario='email', mode='protected')
    asyncio.run(run_email_demo(before, delay=0))
    asyncio.run(run_email_demo(after, delay=0))
    assert before.local_sink and before.snapshot()['summary']['exposures'] > 0
    assert after.local_sink == [] and after.snapshot()['summary']['blocked'] == 2
    assert after.events[-1]['target'] == '/email/demo_inbox.txt' and after.events[-1]['decision'] == 'ALLOW'
    assert evaluate('read_file', '/email/demo_private.txt', EMAIL_SCOPE, True).status == 'BLOCK'


def test_server_delete_is_denied_and_logs_remain_readable():
    session = create_session(scenario='server', mode='protected')
    asyncio.run(run_server_demo(session, delay=0))
    assert any(event['tool'] == 'server.delete' and event['decision'] == 'BLOCK' for event in session.events)
    assert session.events[-1]['target'] == '/server/demo_access.log'
    assert evaluate('server.delete', '/server/demo_config.txt', SERVER_SCOPE, True).status == 'BLOCK'


def test_payment_mismatch_asks_and_does_not_execute():
    session = create_session(scenario='finance')
    run_finance_preview(session)
    assert session.payment_prepared['amount'] == 1250
    requested = execute(session, 'payment.execute', '/finance/demo_payment_profile.json', amount=5000)
    assert requested['event']['decision'] == 'ASK'
    assert '₹1,250' in requested['approval']['reason']
    assert session.demo_payments == []
    unknown = execute(session, 'payment.execute', '/finance/demo_unknown_account.json', amount=5000)
    assert unknown['event']['decision'] == 'ASK'
    assert unknown['approval']['target'] == '/finance/demo_unknown_account.json'
    assert session.demo_payments == []


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
