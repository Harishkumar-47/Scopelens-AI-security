import asyncio
from typing import Literal
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.runtime.lab_service import (SESSIONS, DEFAULT_TASK, create_session, run_coding_demo,
                                     run_finance_preview, request_action, approve_action, compare_replay)

router = APIRouter(prefix='/api/live', tags=['Live Lab'])


class SessionCreate(BaseModel):
    scenario: Literal['coding', 'finance'] = 'coding'
    mode: Literal['protected', 'unprotected'] = 'protected'
    task: str = Field(default=DEFAULT_TASK, min_length=1, max_length=500)
    model: Literal['replay', 'local'] = 'replay'


class ActionRequest(BaseModel):
    tool: Literal['read_file', 'demo_send', 'payment.preview', 'payment.prepare', 'payment.execute']
    target: str = Field(min_length=1, max_length=300)
    amount: int | None = Field(default=None, ge=1, le=100000)


class ApprovalDecision(BaseModel):
    allow: bool


def get_session(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(404, 'Live Lab session not found')
    return session


@router.get('/config')
def config():
    from app.runtime.local_llm import LocalLLMProvider
    provider = LocalLLMProvider()
    return {'default_model': provider.model, 'local_model_enabled': provider.enabled,
            'replay_available': True, 'sandbox_only': True}


@router.get('/tools')
def tools_catalog():
    from app.runtime.policy_engine import TOOL_DEFINITIONS
    return [{'name': name, **definition} for name, definition in TOOL_DEFINITIONS.items()]


@router.post('/sessions')
def new_session(body: SessionCreate):
    session = create_session(body.scenario, body.mode, body.task, body.model)
    return session.snapshot()


@router.get('/sessions')
def list_sessions():
    return [session.snapshot() for session in reversed(list(SESSIONS.values()))]


@router.get('/sessions/{session_id}')
def session_snapshot(session_id: str):
    return get_session(session_id).snapshot()


@router.post('/sessions/{session_id}/run', status_code=202)
async def run_session(session_id: str):
    session = get_session(session_id)
    if session.running or session.completed:
        raise HTTPException(409, 'Session already started')
    if session.scenario == 'finance':
        run_finance_preview(session)
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
async def approval(session_id: str, approval_id: str, body: ApprovalDecision):
    session = get_session(session_id)
    result = approve_action(session, approval_id, body.allow)
    if not result:
        raise HTTPException(404, 'Approval not found or already resolved')
    return {'approval': result, 'session': session.snapshot()}


@router.post('/compare')
async def comparison():
    return await compare_replay()


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
