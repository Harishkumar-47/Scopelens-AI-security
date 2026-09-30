# ScopeLens

**Before you give an AI agent access, see the blast radius.**

ScopeLens is an AI Agent Permission & Blast-Radius Simulator. It reveals risks that arise when individually acceptable permissions combine, then shows what changes if you remove one permission.

## Problem and solution

An agent with customer data and external email access can create an exfiltration path even when each permission looks reasonable alone. ScopeLens maps provider permissions into common capabilities, builds a graph, applies deterministic risk rules, and recalculates everything during least-privilege simulation. AI only explains the deterministic result.

## Core innovation

The before/after simulator removes an actual permission and reruns normalization, graph generation, risk detection and scoring. The demo Support Agent changes from **76 HIGH / 3 chains** to **28 LOW / 0 chains** when `email.send_external` is removed, while customer reading and ticket creation remain available.

## Screenshots

Screenshots can be added after deployment. The app includes a landing page, setup form, interactive graph, scenario gallery and side-by-side comparison page.

## Architecture and stack

React + Vite + TypeScript → FastAPI + Pydantic → provider adapter → normalized capabilities → NetworkX graph → deterministic risk rules and exposure score → simulation → optional OpenAI/Gemini explanation. Cytoscape.js renders the graph. See [architecture](docs/architecture.md) and [risk model](docs/risk-model.md).

## Features

- Manual agent configuration and JSON import
- Three demo agents: Support, DevOps and Finance
- 29 normalized capabilities and 12 deterministic risk rules
- Interactive graph and explicit risk paths
- Permission removal simulation and before/after comparison
- Deterministic purpose alignment and optional AI explanations with fallback
- Simplified MCP, OAuth, AWS IAM, Azure RBAC, GCP IAM and GitHub adapters

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Frontend: <http://localhost:3000>. Backend: <http://localhost:8000>. Swagger: <http://localhost:8000/docs>.

For local development, install Python dependencies from `backend/requirements.txt`, run `uvicorn app.main:app --reload` in `backend`, then run `npm install && npm run dev` in `frontend`.

## Environment

`AI_ENABLED=false` is the default. To enable explanations set `AI_ENABLED=true`, `AI_PROVIDER=openai` or `gemini`, and the corresponding key. The app falls back to deterministic templates if the API is unavailable. `BACKEND_PORT`, `FRONTEND_PORT`, and `CORS_ORIGINS` are configurable. `DATABASE_URL` is reserved for future history support; the MVP stores current analyses in browser session storage.

## API

| Endpoint | Purpose |
| --- | --- |
| `POST /api/analyze` | Analyze agent permissions |
| `POST /api/simulate` | Remove one permission and compare |
| `POST /api/explain` | Explain existing deterministic findings |
| `GET /api/scenarios` | List sample agents |
| `GET /api/scenarios/{id}` | Get one sample |
| `GET /api/providers` | List supported adapters |
| `POST /api/import` | Validate and analyze imported JSON |
| `GET /api/health` | Health status |

`POST /api/analyze` accepts `{ "name": "SupportBot", "purpose": "Answer support tickets", "provider": "generic", "permissions": ["customer.read", "email.send_external"] }`. `POST /api/simulate` accepts `{ "agent": <same object>, "remove_permission": "email.send_external" }`.

## Provider support and MVP limitations

Generic permissions are explicitly mapped. MCP accepts a simplified `manifest.tools[]` with names and normalized capabilities. OAuth accepts `manifest.scopes[]`. AWS IAM accepts `manifest.Statement[]` with `Effect: Allow` and `Action`. Azure, GCP and GitHub accept simplified `actions` or `permissions` arrays. Unknown permissions remain visible and unscored.

**ScopeLens is a hackathon prototype designed to model agent capability combinations.** The MVP does not implement complete cloud IAM or OAuth semantics, IAM conditions, wildcard expansion, resource scoping, deny precedence, or live provider scanning. Provider adapters normalize a supported subset into a common model. Treat ScopeLens as a security design and analysis assistant, not a replacement for provider-native security controls.

## Testing and deployment

Run `PYTHONPATH=. pytest -q` in `backend`, `npm run build` in `frontend`, then `docker compose up --build`. Check `/api/health`, load all three scenarios, simulate the Support Agent, and verify the UI at desktop and mobile widths. See [demo guide](docs/demo-guide.md).

Images are named `scopelens-backend` and `scopelens-frontend`. Publish with `docker tag scopelens-backend <registry>/scopelens-backend:<tag>` and `docker push <registry>/scopelens-backend:<tag>` (similarly for frontend). Docker Hub and GHCR both work. One VM with Docker Compose is simplest; alternatively deploy the frontend to Vercel/Netlify/Cloudflare Pages and backend to Render/Railway/Fly.io, with a same-origin `/api` proxy and CORS configured.

## Roadmap

Real MCP discovery, OAuth scope import, Google Workspace and Microsoft 365 analysis, provider-native GitHub/cloud imports, runtime monitoring, short-lived permissions, approval workflows, policy-as-code export, CI checks and enterprise inventory.
