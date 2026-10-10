import asyncio
import secrets
from typing import Literal
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Header
from pydantic import BaseModel, Field
from app.runtime.local_llm import LocalLLMProvider
from app.runtime.bank_chat import sign_in, ask, model_plan
from app.runtime import practical_lab

from app.runtime.lab_service import (SESSIONS, DEFAULT_TASK, create_session, run_coding_demo,
                                     run_finance_task, run_email_demo, run_server_demo,
                                     request_action, approve_action, compare_replay)

router = APIRouter(prefix='/api/live', tags=['Live Lab'])


class SessionCreate(BaseModel):
    scenario: Literal['coding', 'finance', 'email', 'server'] = 'coding'
    mode: Literal['protected', 'unprotected'] = 'protected'
    task: str = Field(default=DEFAULT_TASK, min_length=1, max_length=500)
    model: Literal['replay', 'local'] = 'replay'


class ActionRequest(BaseModel):
    tool: Literal['read_file', 'demo_send', 'payment.preview', 'payment.prepare', 'payment.execute', 'server.delete']
    target: str = Field(min_length=1, max_length=300)
    amount: int | None = Field(default=None, ge=1, le=100000)


class ApprovalDecision(BaseModel):
    allow: bool


class DemoSignIn(BaseModel):
    pin: str = Field(min_length=1, max_length=40)


class ChatPrompt(BaseModel):
    model: str = Field(default='demo', min_length=1, max_length=150)
    prompt: str = Field(min_length=1, max_length=500)
    token: str = Field(min_length=1, max_length=100)


class PracticalCreate(BaseModel):
    mode: Literal['protected', 'unprotected'] = 'protected'
    model: Literal['qwen', 'demo'] = 'qwen'
    injection: str = Field(default=practical_lab.DEFAULT_INJECTION, max_length=1500)
    delegation_granted: bool = True


class PracticalChat(BaseModel):
    token: str = Field(min_length=1, max_length=100)
    prompt: str = Field(min_length=1, max_length=500)


def get_session(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, 'Live Lab session not found')
    return session


@router.get('/config')
def config():
    provider = LocalLLMProvider()
    status = provider.status()
    return {'default_model': provider.model, 'local_model_enabled': status['ready'],
            'local_model_status': status['status'],
            'replay_available': True, 'sandbox_only': True}


@router.get('/tools')
def tools_catalog():
    from app.runtime.policy_engine import TOOL_DEFINITIONS
    return [{'name': name, **definition} for name, definition in TOOL_DEFINITIONS.items()]


@router.post('/sessions')
def new_session(body: SessionCreate):
    if body.model == 'local' and body.scenario != 'coding':
        raise HTTPException(422, 'Local AI is available for the Code demo only')
    if body.model == 'local':
        status = LocalLLMProvider().status()
        if not status['ready']:
            raise HTTPException(409, f"{status['model']} is {status['status'].replace('_', ' ')}. Select Demo AI.")
    session = create_session(body.scenario, body.mode, body.task, body.model)
    return {**session.snapshot(), 'owner_token': session.owner_token}


@router.get('/sessions')
def list_sessions():
    return [session.snapshot() for session in reversed(list(SESSIONS.values()))]


@router.get('/sessions/{session_id}')
def session_snapshot(session_id: str):
    return get_session(session_id).snapshot()


@router.post('/sessions/{session_id}/bank-sign-in')
def bank_sign_in(session_id: str, body: DemoSignIn):
    session = get_session(session_id)
    if session.scenario != 'finance':
        raise HTTPException(422, 'Bank chat is available for the Payments demo only')
    token = sign_in(session, body.pin)
    if token is None:
        raise HTTPException(401, 'Incorrect demo operator PIN')
    return {'token': token}


@router.post('/sessions/{session_id}/bank-chat')
async def bank_chat(session_id: str, body: ChatPrompt):
    import secrets
    session = get_session(session_id)
    if session.scenario != 'finance':
        raise HTTPException(422, 'Bank chat is available for the Payments demo only')
    if not session.auth_token or not secrets.compare_digest(body.token, session.auth_token):
        raise HTTPException(401, 'Sign in to the demo bank agent first')
    if session.running:
        raise HTTPException(409, 'Bank agent is working')
    session.running = True
    try:
        plan = None
        if body.model != 'demo':
            if body.model not in await asyncio.to_thread(LocalLLMProvider().installed_models):
                raise HTTPException(409, 'Selected bank model is not installed. Refresh models.')
            try:
                plan = await asyncio.to_thread(model_plan, session, body.prompt, body.model)
            except ValueError as error:
                raise HTTPException(502, str(error)) from error
        session.model_used = 'Demo AI · scripted' if body.model == 'demo' else body.model
        return ask(session, body.prompt, plan)
    finally:
        session.running = False
        session.publish()


@router.post('/practical/sessions')
def practical_create(body: PracticalCreate):
    if body.model == 'qwen' and not LocalLLMProvider().status()['ready']:
        raise HTTPException(409, 'Local Qwen is unavailable. Select Demo AI or start Ollama.')
    return practical_lab.create(body.mode, body.model, body.injection, body.delegation_granted).snapshot()


@router.get('/practical/sessions/{session_id}')
def practical_snapshot(session_id: str):
    session = practical_lab.SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(404, 'Practical test session not found')
    return session.snapshot()


@router.post('/practical/sessions/{session_id}/sign-in')
def practical_sign_in(session_id: str, body: DemoSignIn):
    session = practical_lab.SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(404, 'Practical test session not found')
    token = practical_lab.authenticate(session, body.pin)
    if token is None:
        raise HTTPException(401, 'Incorrect demo operator PIN')
    return {'token': token, 'session': session.snapshot()}


@router.post('/practical/sessions/{session_id}/chat')
async def practical_chat(session_id: str, body: PracticalChat):
    session = practical_lab.SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(404, 'Practical test session not found')
    if not session.token or not secrets.compare_digest(body.token, session.token):
        raise HTTPException(401, 'Sign in to the demo bank agent first')
    if session.busy:
        raise HTTPException(409, 'The model is still working')
    return await practical_lab.chat(session, body.prompt)


@router.post('/sessions/{session_id}/run', status_code=202)
async def run_session(session_id: str):
    session = get_session(session_id)
    if session.running or session.completed:
        raise HTTPException(409, 'Session already started')
    if session.scenario == 'finance':
        run_finance_task(session)
    elif session.scenario == 'email':
        session.running = True
        session.publish()
        asyncio.create_task(run_email_demo(session))
    elif session.scenario == 'server':
        session.running = True
        session.publish()
        asyncio.create_task(run_server_demo(session))
    else:
        session.running = True
        session.publish()
        asyncio.create_task(run_coding_demo(session))
    return session.snapshot()


@router.post('/sessions/{session_id}/actions')
async def action(session_id: str, body: ActionRequest):
    session = get_session(session_id)
    result = request_action(session, body.tool, body.target, body.amount)
    return {'result': result, 'session': session.snapshot()}


@router.post('/sessions/{session_id}/approvals/{approval_id}')
async def approval(session_id: str, approval_id: str, body: ApprovalDecision, authorization: str | None = Header(default=None)):
    from app.runtime.integration import owned
    session = owned(session_id, authorization)
    result = approve_action(session, approval_id, body.allow)
    if not result:
        raise HTTPException(404, 'Approval not found or already resolved')
    return {'approval': result, 'session': session.snapshot()}


@router.post('/compare')
async def comparison(scenario: Literal['coding', 'finance', 'email', 'server'] = 'finance', captured_id: str | None = None):
    try:
        return await compare_replay(scenario, captured_id)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.websocket('/ws/{session_id}')
async def session_stream(websocket: WebSocket, session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=8)
    session.subscribers.add(queue)
    try:
        await websocket.send_json({'type': 'snapshot', 'session': session.snapshot()})
        while True:
            await websocket.send_json(await queue.get())
    except WebSocketDisconnect:
        pass
    finally:
        session.subscribers.discard(queue)
