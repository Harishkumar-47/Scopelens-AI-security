"""Persistent metadata-only evidence; never persist file contents or raw prompts."""
import json
import hashlib
import os
import sqlite3
from pathlib import Path
from threading import RLock
from contextlib import contextmanager

LOCK = RLock()

@contextmanager
def connect():
    path = Path(os.getenv('AUDIT_DB', '/tmp/scopelens/evidence.sqlite3'))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, session TEXT, at TEXT, payload TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, at TEXT, payload TEXT)')
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def record(session, event):
    payload = {key: event.get(key) for key in ('id', 'at', 'tool', 'target', 'decision', 'reason', 'classification', 'amount', 'approval_id', 'execution')}
    payload.update(session_id=session.id, agent=session.agent_name,
                   task='[redacted user task]', job=session.scenario, task_sha256=hashlib.sha256(session.task.encode()).hexdigest(),
                   source=event.get('instruction_source') or ('untrusted input' if event.get('untrusted_source') else 'user / workflow'),
                   rule='Intent Lock' if session.intent else 'sandbox scenario policy')
    with LOCK, connect() as db:
        snapshot = {'id': session.id, 'scenario': session.scenario, 'mode': session.mode, 'agent': session.agent_name, 'state': session.execution_state(), 'model': session.model_used, 'task': '[redacted user task]'}
        db.execute('INSERT OR REPLACE INTO sessions VALUES (?, ?, ?)', (session.id, event['at'], json.dumps(snapshot)))
        db.execute('INSERT OR REPLACE INTO evidence VALUES (?, ?, ?, ?)',
                   (event['id'], session.id, event['at'], json.dumps(payload)))

def report(session_id=None):
    with LOCK, connect() as db:
        rows = db.execute('SELECT payload FROM evidence WHERE session = ? ORDER BY rowid', (session_id,)) if session_id else db.execute('SELECT payload FROM evidence ORDER BY rowid DESC LIMIT 1000')
        return [json.loads(row[0]) for row in rows]

def session_history():
    with LOCK, connect() as db:
        return [json.loads(row[0]) for row in db.execute('SELECT payload FROM sessions ORDER BY at DESC LIMIT 1000')]
