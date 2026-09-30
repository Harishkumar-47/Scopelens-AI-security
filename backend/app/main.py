import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from app.models import AgentInput, SimulationInput, ExplanationInput
from app.engine.analyzer import analyze
from app.ai.explainer import explain
import os

app = FastAPI(title='ScopeLens API', version='0.1.0')
origins = [o.strip() for o in os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',') if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])
SCENARIO_DIR = Path(__file__).parent / 'scenarios'

@app.get('/api/health')
def health():
    return {'status': 'ok', 'service': 'scopelens-backend'}

@app.post('/api/analyze')
def analyze_api(agent: AgentInput):
    return analyze(agent)

@app.post('/api/simulate')
def simulate_api(body: SimulationInput):
    before = analyze(body.agent)
    available = [i['permission'] for i in before['normalized_permissions']]
    if body.remove_permission not in available:
        raise HTTPException(400, 'Permission is not present in the agent')
    updated = body.agent.model_copy(deep=True)
    if body.remove_permission in updated.permissions:
        updated.permissions.remove(body.remove_permission)
    elif updated.provider == 'mcp' and updated.manifest:
        for tool in updated.manifest.get('tools', []):
            tool['capabilities'] = [capability for capability in tool.get('capabilities', [])
                                    if f"mcp.{tool['name']}.{capability}" != body.remove_permission]
    elif updated.manifest:
        for field in ('scopes', 'actions', 'permissions'):
            if body.remove_permission in updated.manifest.get(field, []):
                updated.manifest[field].remove(body.remove_permission)
        statements = updated.manifest.get('Statement', [])
        if isinstance(statements, dict):
            statements = [statements]
        for statement in statements:
            actions = statement.get('Action', [])
            if isinstance(actions, list) and body.remove_permission in actions:
                actions.remove(body.remove_permission)
            elif actions == body.remove_permission:
                statement['Action'] = []
    after = analyze(updated)
    return {'before': before, 'after': after,
            'difference': {'score_change': after['score'] - before['score'],
                           'removed_risks': [r['id'] for r in before['risks'] if r['id'] not in {a['id'] for a in after['risks']}],
                           'removed_permission': body.remove_permission}}

@app.get('/api/scenarios')
def scenarios():
    return [{'id': p.stem, **json.loads(p.read_text())} for p in sorted(SCENARIO_DIR.glob('*.json'))]

@app.get('/api/scenarios/{scenario_id}')
def scenario(scenario_id: str):
    path = SCENARIO_DIR / f'{scenario_id}.json'
    if not path.is_file() or path.parent != SCENARIO_DIR:
        raise HTTPException(404, 'Scenario not found')
    return {'id': scenario_id, **json.loads(path.read_text())}

@app.get('/api/providers')
def providers():
    return [{'id': id_, 'label': label} for id_, label in [
        ('generic', 'Generic Agent'), ('mcp', 'MCP Agent'), ('oauth', 'OAuth App'),
        ('aws_iam', 'AWS IAM'), ('azure_rbac', 'Azure RBAC'),
        ('gcp_iam', 'GCP IAM'), ('github', 'GitHub App')]]

@app.post('/api/import')
def import_agent(payload: dict):
    try:
        agent = AgentInput.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(422, exc.errors(include_context=False, include_input=False)) from exc
    return {'agent': agent.model_dump(), 'analysis': analyze(agent)}

@app.post('/api/explain')
def explain_api(body: ExplanationInput):
    return explain(body.agent, analyze(body.agent))
