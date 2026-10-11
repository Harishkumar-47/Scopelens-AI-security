# Low-resource ScopeLens validation — 2026-10-11

Performed on the existing develop checkout, CachyOS, 7,779 MiB physical RAM.

## Inventory and cleanup

- No host `ollama` binary or `ollama.service` was installed. No model container was running initially.
- ScopeLens had a stopped llama.cpp container configured with **Qwen3 0.6B**, not a Llama-family model. Its stopped container and model volume are preserved.
- ScopeLens's own Ollama volume contained `qwen3:0.6b` (522 MB) and `qwen3:4b` (2.5 GB).
- After showing the proposed deletion and verifying real 0.6B inference, stopped/unloaded and removed only `qwen3:4b` using Ollama. Other projects' containers and volumes were untouched.
- Pulled and verified `qwen3:0.6b`, digest `7df6b6e09427`, Q4_K_M, Ollama 0.35.0. No fallback download was necessary.

## Configuration

One Ollama Compose service, CPU-only requests, two threads, context 2,048 tokens, at most 256 output tokens, thinking disabled, one concurrent backend inference, one loaded model, queue limit two, 60-second keep-alive, 180-second model request timeout. Backend HTTP client errors propagate without scripted fallback. Frontend requests have a 300-second bound; nginx allows 310 seconds for multi-turn chat.

Runtime limits: Ollama 1,536 MiB / two CPUs; FastAPI 384 MiB / one CPU; nginx 128 MiB / half a CPU. The old automatically downloaded llama.cpp Compose service is removed; its external adapter remains opt-in through `LLAMA_CPP_BASE_URL`. Actual installed models are discovered through Ollama tags. Availability polling never loads a runner. Live views and Practical Test refresh availability every ten seconds. `/practical` now renders its existing page instead of redirecting to Tester. Demo AI remains explicitly selectable.

Practical Test proposes structured actions using [Ollama JSON-schema output](https://docs.ollama.com/capabilities/structured-outputs). Independent backend validation rejects unknown tools, extra arguments and oversized plans before execution. Grants, policy checks, owner approvals and sandbox boundaries remain independent of inference.

The backend image copies application code after cached dependency and user setup layers, so source-only rebuilds do not repeat those setup steps.

## Observed resource use

Initial host `free -m`: 3,943 MiB used / 3,836 MiB available, all ScopeLens services stopped. The final idle-model host snapshot was 5,126 MiB used / 2,652 MiB available. Docker reported Ollama 12.48 MiB, FastAPI 16.06 MiB and nginx 2.41 MiB (30.95 MiB combined). Runtime snapshots include unrelated desktop applications and build/browser activity, so these totals are not an isolated RAM savings benchmark.

Measured loaded Qwen runner: 781,556,119 bytes (745 MiB), context 2,048, VRAM zero. Before the last service restart, kernel counters recorded a 1,139 MiB Ollama container memory peak, zero memory-limit hits and zero OOM kills. A fresh cold load took 20.6 seconds and returned **“2 plus 2 equals 4.”** Idle service snapshots: FastAPI about 47–50 MiB, nginx about 8–10 MiB, Ollama about 15–54 MiB after unload. `/api/ps` returned an empty models array after inactivity while model availability still correctly reported ready.

Heavy disk stalls during image commits and background desktop activity caused 90-second cold-load timeouts and a slow initial Live browser comparison. The final model timeout is 180 seconds, with a 60-second idle keep-alive to avoid unnecessary reloads between chat stages. Another browser run exposed unsupported model action fields; strict validation rejected them without executing requests. Schema-constrained output repairs this small-model integration. No backend protection was weakened. Tests use temporary RAM-backed SQLite files to avoid disk contention; production evidence stays in the persistent Compose audit volume.

## Verification

- Backend suite: **77 passed**, one upstream Starlette/AnyIO deprecation warning.
- Frontend TypeScript/Vite build: passed locally and inside Docker.
- Compose configuration: passed; all final services reached healthy status.
- Real deployed inference: Qwen generated a project README tool request and a bill-summary reply in authenticated Practical Test.
- OFF/ON comparisons: coding, bank, email and server requests independently executed or denied with verified sandbox state.
- Owner authorization, one-use approval, missing-model errors, redacted evidence: passed.
- Ollama stopped deliberately: all four Live replay scenarios continued enforcing policy and legitimate sandbox access; service restarted afterward.
- Final real deployment acceptance with the 180-second timeout and 60-second keep-alive: all checks passed, including the actual Qwen reply “Your synthetic electricity invoice for INV-DEMO-104 shows Priya Example owes ₹1,250, due next week.”
- Final desktop Chromium suite against Compose: **6 passed**, including real Qwen availability and authenticated Practical Test chat.

## Start

```bash
docker compose --profile live-model up -d ollama
docker compose exec ollama ollama pull qwen3:0.6b
docker compose --profile live-model up -d --build --wait
```

Use the existing `.env`, or copy `.env.example` for a fresh checkout. Frontend: http://localhost:3000; Practical Test: http://localhost:3000/practical; API docs: http://localhost:8000/docs; health: http://localhost:8000/api/health; availability: http://localhost:8000/api/live/config; model list: http://localhost:8000/api/tester/models; Ollama: http://localhost:11434.

For an existing shared host Ollama, point `LLM_BASE_URL` at its Docker-reachable endpoint and start only backend/frontend without the `live-model` profile. The host service must accept connections from the Docker bridge. Do not start another model service.

```bash
python scripts/validate_deployment.py
# After deliberately stopping Ollama:
python scripts/verify_offline.py
# Run from frontend/ with services running:
TEST_LOCAL_MODEL=true npx playwright test --project=desktop
```
