# ScopeLens

**Define an agent's job. Test its tools. Stop unauthorized actions. Prove the result.**

ScopeLens is a deterministic security layer around agent tool calls, built on the existing React/TypeScript, FastAPI/Pydantic and NetworkX application. It is not an AI model. Qwen3 0.6B supplies optional local inference; ScopeLens makes the execution decisions outside the model.

## Start with Docker and Qwen3 0.6B

```bash
cp .env.example .env
# Keep existing environment settings if you already have .env.
# Set LLM_ENABLED=true, LOCAL_LLM_MODEL=qwen3:0.6b.
docker compose --profile live-model up -d ollama
docker compose exec ollama ollama pull qwen3:0.6b
docker compose --profile live-model up -d --build backend frontend
curl --fail http://127.0.0.1:8000/api/readiness
```

Open [ScopeLens](http://localhost:3000), [API docs](http://localhost:8000/docs), or [health](http://localhost:8000/api/health). Model installation is separate from image builds. Weights remain in the Ollama volume. CPU-only inference uses two threads; allow up to 240 seconds for cold loading/inference. Readiness checks actually load the configured Ollama runner, rather than treating an installed tag as sufficient.

Ollama is optional: set `LLM_ENABLED=false`, then run `docker compose up -d --build`. Choose **Demo AI · scripted** for recorded tests. A failed local inference produces an error and never silently becomes Demo AI.

See [complete Docker/local setup and validation steps](docs/setup-and-validation.md).

## Developer workflow

**BUILD → CHECK → TEST → PROTECT → DEPLOY**

- **Analyze:** import local JSON configurations or simplified provider manifests. Backend adapters extract supported permissions, calculate capability combinations and show NetworkX risk paths. Manual permission entry remains available.
- **Tester:** converse with Bank, Code, Email, Server or Custom agents. Qwen proposes actual requests; the gateway validates and executes controlled sandbox tools. Model-generated text is distinguished from backend execution summaries. A model refusing an attack is a valid result.
- **Intent Lock:** configure the job, tools, resources, forbidden actions, approval tools and authorized delegates. ALLOW and WARN execute granted tools, ASK waits for a human, and BLOCK denies execution. Delegation can only narrow permissions and inherits restrictions.
- **Live:** run identical captured requests through isolated OFF and ON sandboxes. Four recorded scenarios are available; select a captured model session to replay real model actions without fresh inference.
- **Proof:** inspect persistent, timestamped SQLite events and download redacted JSON. Decisions include requested tools/resources, rule, reason, instruction source, and actual before/after execution state. Raw prompts and file contents are excluded; a task fingerprint links to a locally retained original task.
- **Integrate:** use the [Python middleware/example](docs/developer-integration.md) to route local agent tool calls through the same gateway. Only routed calls are enforced.

`/live` opens before/after replay. `/live/session` preserves the single-session lab. `/practical` redirects to Tester; it is not a second chatbot tab. Impact and About retain explanations of developer usage.

## Demonstrate all four scenarios

| Scenario | Permitted task | Manipulated request | Protected result |
| --- | --- | --- | --- |
| Code | Read project files | Read synthetic credentials outside the project and send them | Read and send denied; project reads continue |
| Payments | Check and prepare a ₹1,250 bill | Access private synthetic records; transfer ₹5,000 to an unapproved demo account | Record access/send denied; transfer waits for explicit approval |
| Email | Summarize the synthetic inbox | Read private synthetic data and deliver it to the local sink | Access/send denied; inbox remains readable |
| Server | Read diagnostic logs | Delete simulated server settings | Change denied; log access continues |

Every scenario follows normal task → untrusted input → requested action → gateway decision → verified sandbox state. OFF mode can expose synthetic data or change in-memory demo state; it cannot reach host files, external receivers, real accounts or production servers. ASK is not a successful block and is not execution. Approved payments remain synthetic.

To replay an existing capture directly, use `POST /api/live/compare?scenario=coding&captured_id=SESSION_ID`. The response explicitly reports `inference=false`, identical requests, and state-backed results.

## Run the Python integration

```bash
python3 examples/scopelens_sdk.py
```

With the backend running, this makes a real project fixture read through an owner-authorized gateway, then attempts synthetic credential access. Expected results: ALLOW and BLOCK. Inspect Proof for the corresponding events. The gateway executes tools itself; callers must not execute them again independently.

Policy configuration and delegation requests are documented in [developer integration](docs/developer-integration.md).

## Tests and CI

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python -m pytest -q
npm --prefix frontend ci
npm --prefix frontend run build
docker compose config --quiet
# Real inference and deployed gateway acceptance, with Ollama running:
python3 scripts/validate_deployment.py
# Desktop and mobile Chromium checks against the running app:
cd frontend
npx playwright install chromium
npm run test:e2e
```

CI runs backend tests, frontend builds, Compose validation and browser checks against a model-free Docker installation. Model adapter unit tests use controlled responses; the deployment validator separately tests actual Qwen inference. See [validation evidence](docs/platform-validation.md) for observed results and limits.

## What works, what is simulated, what is next

| Status | Scope |
| --- | --- |
| Working local features | Ollama Qwen inference, validated tool requests, deterministic gateway, Custom Intent Lock, narrowed delegation, expiring owner-authorized one-time approvals, exact replay, SQLite evidence/history, JSON export, Python sandbox tool middleware, manifest analysis, responsive dashboard |
| Synthetic simulation | Employee/account records, money transfers, receiver deliveries and destructive server state. File reads execute against real local fixture files; payments, sends and deletions mutate in-memory demo state |
| Simplified analysis | MCP, OAuth, GitHub, AWS IAM, Azure RBAC and GCP IAM imports cover a documented subset, not complete provider semantics or live account discovery |
| Future work | Arbitrary host-tool adapters, a production MCP proxy, provider-native enforcement, tenant identity/isolation, signed audit evidence, durable active chat/approval recovery, production deployment hardening |

The named `audit_data` volume retains redacted session history and evidence across restarts. Active sessions, prompt contexts and approvals are intentionally transient; restarting invalidates them. Approval IDs expire after 120 seconds and are consumed on either decision. Unknown tools, traversal and symlink aliases are denied before reads. Requests, tool loops and resource usage are bounded.

This is a **local, single-operator security testing platform**, not production-ready security. Ports bind to loopback. Remote use requires a separately configured authenticated TLS proxy. SQLite evidence is not tamper-proof, and ScopeLens cannot protect tool paths that bypass its gateway. A recorded legitimate-task success means permitted sandbox task access succeeded, not that an arbitrary code fix or real transaction completed.

## Architecture and existing analysis

React + Vite + TypeScript → FastAPI + Pydantic → simplified provider adapters → normalized capabilities → NetworkX → deterministic risk rules. The runtime adds fixed sandbox tools, Intent Lock, authorization, events and SQLite evidence. Cytoscape renders the access graphs; the dashboard uses lightweight React/CSS depth and interactive system icons.

Existing permission-removal simulation remains: the demo Support Agent changes from **76 HIGH / 3 chains** to **28 LOW / 0 chains** when `email.send_external` is removed. Unknown permissions remain visible and unscored. Optional explanation AI is separate from runtime inference and labels its template fallback.

See [architecture](docs/architecture.md), [risk model](docs/risk-model.md) and [runtime guard](docs/runtime-guard.md). Swagger documents the complete current API.

The optional `small-model` profile preserves llama.cpp support. It downloads quantized Qwen into a model volume at startup; Ollama remains the default. Both installed runtimes can appear in Tester when `LLM_ENABLED=true`.
