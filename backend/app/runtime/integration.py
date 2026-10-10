"""Local HTTP tool gateway used by the Python SDK. Fixed synthetic tools only."""
import secrets
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from app.runtime.intent_lock import IntentLock
from app.runtime.lab_service import create_session, SESSIONS
from app.runtime.tool_gateway import execute, resolve_approval
from app.runtime.evidence import report, session_history

router = APIRouter(prefix='/api/gateway', tags=['Intent Lock'])
class Configure(BaseModel):
    policy: IntentLock
class ToolCall(BaseModel):
    tool: str = Field(min_length=1, max_length=60)
    target: str = Field(min_length=1, max_length=300)
    amount: int | None = Field(default=None, ge=1, le=100000)
    untrusted: bool = False
class Approve(BaseModel):
    allow: bool
class Delegate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    policy: IntentLock

def owned(id, authorization):
    session = SESSIONS.get(id)
    if not session or not authorization or not secrets.compare_digest(authorization, 'Bearer '+session.owner_token):
        raise HTTPException(401, 'Session owner authorization required')
    return session

@router.post('/sessions')
def configure(body: Configure):
    session = create_session(task=body.policy.job)
    session.intent = body.policy
    return {'id': session.id, 'token': session.owner_token, 'policy': session.intent.model_dump()}

@router.post('/sessions/{id}/tools')
def tool(id: str, body: ToolCall, authorization: str | None = Header(default=None)):
    session = owned(id, authorization)
    result = execute(session, body.tool, body.target, amount=body.amount, untrusted_source=body.untrusted)
    # Only permitted reads return data; a previous read must never leak on denial.
    return {**result, 'content': session.last_read_content if body.tool == 'read_file' and result['event']['decision'] in ('ALLOW','WARN') else None,
            'state': session.execution_state()}

@router.post('/sessions/{id}/delegate')
def delegate(id: str, body: Delegate, authorization: str | None = Header(default=None)):
    parent = owned(id, authorization)
    try:
        policy = parent.intent.delegate(body.name, body.policy)
    except ValueError as error:
        raise HTTPException(403, str(error)) from error
    child = create_session(task=policy.job)
    child.intent = policy
    child.agent_name = body.name
    return {'id': child.id, 'token': child.owner_token, 'policy': policy.model_dump()}

@router.post('/sessions/{id}/approvals/{approval_id}')
def approve(id: str, approval_id: str, body: Approve, authorization: str | None = Header(default=None)):
    session = owned(id, authorization)
    result = resolve_approval(session, approval_id, body.allow)
    if result is None:
        raise HTTPException(404, 'Approval expired or already consumed')
    return {'approval': result, 'state': session.execution_state()}

@router.get('/proof')
def proof():
    return {'redacted': True, 'events': report(), 'sessions': session_history()}
