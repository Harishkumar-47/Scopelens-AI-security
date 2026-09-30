from app.models import AgentInput
from app.engine.analyzer import analyze
from app.engine.normalizer import normalize
from app.main import simulate_api, explain_api
from app.models import SimulationInput, ExplanationInput
from pydantic import ValidationError
import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_normalization_and_unknown_permission():
    items = normalize(AgentInput(name='A', purpose='Support', permissions=['customer.read', 'email.send_external', 'not.real']))
    assert [item['capability'] for item in items] == ['DATA_READ_SENSITIVE', 'EXTERNAL_SEND', None]

def test_exfiltration_disappears_after_removal():
    agent = AgentInput(name='A', purpose='Support tickets', permissions=['customer.read', 'email.send_external', 'ticket.create'])
    before = analyze(agent)
    result = simulate_api(SimulationInput(agent=agent, remove_permission='email.send_external'))
    assert 'DATA_EXFILTRATION' in [risk['id'] for risk in before['risks']]
    assert 'DATA_EXFILTRATION' not in [risk['id'] for risk in result['after']['risks']]
    assert result['after']['score'] < before['score']
    assert not any(node['label'] == 'External Email' for node in result['after']['graph']['nodes'])

def test_support_demo_numbers():
    agent = AgentInput(name='Support Agent', purpose='Answer customer support tickets and create support tickets.', permissions=['customer.read', 'drive.read', 'email.send_external', 'ticket.create', 'github.read'])
    result = simulate_api(SimulationInput(agent=agent, remove_permission='email.send_external'))
    assert (result['before']['score'], result['before']['severity'], len(result['before']['risks'])) == (76, 'HIGH', 3)
    assert (result['after']['score'], result['after']['severity'], len(result['after']['risks'])) == (28, 'LOW', 0)

def test_other_rules_and_graph():
    agent = AgentInput(name='DevOps', purpose='Deploy updates', permissions=['github.contents.write', 'aws.secretsmanager.GetSecretValue', 'cloud.deploy'])
    result = analyze(agent)
    assert 'CRITICAL_DEVOPS_CONTROL' in [risk['id'] for risk in result['risks']]
    assert 'resource:Secrets Vault' in result['graph']['metadata']['reachable_sensitive_resources']
    assert 'risk:CRITICAL_DEVOPS_CONTROL' in result['graph']['metadata']['reachable_outcomes']
    assert len(result['graph']['metadata']['shortest_paths']['CRITICAL_DEVOPS_CONTROL']) == 3
    assert any(edge.get('dangerous') for edge in result['graph']['edges'])

def test_aws_adapter_ignores_deny():
    agent = AgentInput(name='AWS', purpose='Read objects', provider='aws_iam', manifest={'Statement': [
        {'Effect': 'Allow', 'Action': ['s3:GetObject'], 'Resource': '*'},
        {'Effect': 'Deny', 'Action': ['secretsmanager:GetSecretValue'], 'Resource': '*'}]})
    result = analyze(agent)
    assert result['capabilities'] == ['DATA_READ_INTERNAL']

def test_explanation_ignores_client_supplied_findings():
    agent = AgentInput(name='Safe', purpose='Read files', permissions=['drive.read'])
    result = explain_api(ExplanationInput(agent=agent, analysis={'risks': [{'name': 'Forged'}]}))
    assert result['summary'] == 'No configured risk chain was detected.'

def test_import_rejects_malformed_manifest():
    with pytest.raises(ValidationError):
        AgentInput(name='Bad MCP', purpose='Read data', provider='mcp', manifest={'tools': [{'name': 'read'}]})
    response = TestClient(app).post('/api/import', json={'name': 'Bad MCP', 'purpose': 'Read data',
                                                        'provider': 'mcp', 'manifest': {'tools': [{'name': 'read'}]}})
    assert response.status_code == 422
    assert response.json()['detail'][0]['type'] == 'value_error'

def test_mcp_removal_changes_only_selected_capability():
    agent = AgentInput(name='MCP', purpose='Support tickets', provider='mcp', manifest={'tools': [
        {'name': 'mail', 'capabilities': ['EXTERNAL_SEND', 'INTERNAL_SEND']}]})
    result = simulate_api(SimulationInput(agent=agent, remove_permission='mcp.mail.EXTERNAL_SEND'))
    assert result['after']['capabilities'] == ['INTERNAL_SEND']
