# Setup and validation

## Docker with CPU-only Ollama

```bash
cp .env.example .env
# If keeping an existing .env: set LLM_ENABLED=true and LOCAL_LLM_MODEL=qwen3:0.6b.
docker compose --profile live-model up -d ollama
docker compose exec ollama ollama pull qwen3:0.6b
docker compose --profile live-model up -d --build backend frontend
docker compose ps
curl --fail http://127.0.0.1:8000/api/readiness
```

Open http://localhost:3000. The model is pulled into a named volume separately; no model weights or credentials are copied into images. No GPU is required. Ollama is limited to two CPUs, 3 GiB memory, one loaded model and one parallel inference. Cold model loading can take up to 240 seconds. The first readiness check performs an actual runner load; installed tags alone do not prove readiness.

Ollama is optional. For recorded/scripted sandbox testing only, set `LLM_ENABLED=false` and run `docker compose up -d --build`. Demo AI is explicitly scripted; it is never substituted for failed inference. Disconnected runtimes, malformed model JSON, and inference timeouts report errors. Run the readiness endpoint again after recovery.

All exposed application ports bind to loopback by default. SQLite evidence and redacted session history persist in `audit_data`; Ollama weights persist in `ollama_models`. Do not delete these volumes to upgrade. Active chat contexts and approvals are deliberately transient and are invalidated on restart. The app is for local, single-operator use; expose it remotely only behind a separately configured authenticated TLS reverse proxy. It does not provide tenant isolation or tamper-proof audit signing.

## Local development

Use Python 3.12+ and Node 22:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
# Run in one terminal, with a separately started native Ollama installation:
LLM_ENABLED=true LLM_BASE_URL=http://127.0.0.1:11434 .venv/bin/uvicorn app.main:app --app-dir backend --port 8000
# In another terminal:
cd frontend
npm ci
npm run dev
```

For native Ollama, pull `qwen3:0.6b` using `ollama pull qwen3:0.6b`. The Docker-internal hostname `ollama` is not reachable from a native backend. Frontend development proxies `/api` to localhost:8000.

## Demonstration

1. **Live → before/after:** choose Code, Payments, Email or Server. A recorded action list runs through both modes. Inspect deliveries, payments, server state, and pending approvals. Protection OFF remains a fixed synthetic sandbox.
2. **Tester:** choose an installed model or explicitly labeled Demo AI. Try a normal request, then an untrusted-input example. Real models may refuse an attack. This is a real result, not a failed demo.
3. **Tester → replay:** inference proposes actions once; the same actions execute in isolated OFF and ON sessions. Replay is not fresh inference. A refusal produces no unsafe actions to block.
4. **Custom Agent:** configure Intent Lock's job, tools, resources, forbidden actions, approvals and delegates. Only synthetic resource paths are executable. Configuration changes create a new session.
5. **Proof:** refresh and download redacted JSON. A denied tool event has `execution.executed=false` and identical before/after sandbox state. Inspect redacted persistent session history through `/api/gateway/proof`.
6. **Python example:** run `python3 examples/scopelens_sdk.py`. Project content is allowed; credential access is denied at execution.

For an already captured model action list, call `POST /api/live/compare?scenario=coding&captured_id=SESSION_ID`. This replays the existing list without calling the model again. The response labels `inference=false` and includes `captured_requests` and `same_requests`.

## Tests

```bash
.venv/bin/python -m pytest -q
npm --prefix frontend run build
docker compose config --quiet
# Against a running Docker deployment with real Qwen installed:
python3 scripts/validate_deployment.py
```

The unit suite mocks model responses where appropriate. The deployment validator makes actual HTTP inference requests and asserts identical replay actions, state-backed protection, approval authorization/reuse, unavailable-model errors, and redacted evidence. Do not describe mocked model tests as proof of real inference.

## Enforcement and evidence limits

ALLOW and WARN execute granted sandbox tools; WARN records the risk. ASK waits for an authorized human; BLOCK denies execution. Every decision is made in Python, outside the model. No model can execute shell commands, read arbitrary host paths, send external network traffic, operate real accounts, or modify production servers.

Payments, receiver deliveries, and destructive server changes are in-memory simulations; file reads are real reads of fixed synthetic fixtures. `legitimate_task_succeeded` records successful permitted sandbox task access, not an arbitrary code fix or a production transaction. Raw prompts, file content, bearer tokens and real secrets are not stored in evidence. A SHA-256 task fingerprint links evidence to a locally retained original task without storing its text. Task text is redacted in persistent reports; live contexts are ephemeral. SQLite evidence can be modified by its local database owner and is not a signed security attestation.

## Desktop and mobile browser checks

```bash
npm --prefix frontend ci
cd frontend
npx playwright install chromium
npm run test:e2e
```

Tests target the running Docker frontend on port 3000. Set `FRONTEND_URL=http://127.0.0.1:5173` to test a development preview. Ten checks cover desktop/mobile workflow interaction, identical replay outcomes, authenticated approvals, custom policy, Proof download, and manifest import. CI also runs these against a fresh model-free Docker deployment.

`LLM_TIMEOUT_SECONDS` defaults to 240 (bounded to 15–300). CPU inference uses two threads and a 128-token batch, with a 2048-token context. The model stays loaded for 30 minutes; this avoids repeated cold loads during interactive testing. Timeouts are reported explicitly and never trigger a scripted fallback.
