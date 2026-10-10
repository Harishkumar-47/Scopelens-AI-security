# Tester update validation — 2026-10-07

The existing project and its uncommitted Live/Practical/Bank work were extended in place.

## Passed

- Frontend TypeScript compilation and Vite production build. Vite reports the existing large JavaScript chunk warning.
- Backend suite: **47 tests passed**, including 19 new Tester cases. Real FastAPI requests were exercised with TestClient.
- Protected Bank/Code/Email tests intercept the actual file-read call and assert the sensitive file is never opened.
- All four Demo AI attack comparisons: identical agent, task, model and tool requests; unprotected synthetic execution, protected interception; permitted read executed after the unsafe request.
- Bank normal work, exposed synthetic employee data, ₹5,000 fake transfer, approval denial/allowance, and rejection of reused approval IDs.
- Code credential access, email private-data send, and in-memory server deletion.
- Existing Live Code and Bank comparison paths, existing bank authentication and WebSocket tests, and analyzer tests.
- Installed-model catalog validation, discovery parser, model failure without replay, and gateway enforcement for model-proposed/unknown tools. Model responses were mocked for these integration tests.
- Static React route rendering for Tester, Impact, and Live comparison. This does not verify browser interactions or responsive layout.
- `docker compose config --quiet`, Python compilation, and `git diff --check`.

## Environment and remaining checks

The host initially lacked FastAPI, NetworkX, Starlette and HTTPX. PyPI installation failed because DNS/network access is restricted. Tests used read-only cached wheels extracted into `/tmp` (FastAPI 0.115.12, NetworkX 3.4.2, Starlette 0.46.2, HTTPX 0.28.1), with host Python 3.14/Pydantic. The sandbox blocks socket wakeups; a `/tmp`-only event-loop polling helper allowed ASGI test threads to progress without changing application decisions or test assertions. FastAPI reports Python 3.14 deprecation warnings. The pinned Docker Python 3.12 environment was not tested.

`docker compose up -d --build` failed with permission denied on `/var/run/docker.sock`. Configuration validation passed, but containers were not started.

Vite and Uvicorn could not bind listening ports in the sandbox. Headless Firefox exited with status 139. Browser interaction, desktop/mobile appearance, dark-mode appearance, and a full browser-to-container demo remain unverified. Responsive breakpoints and reduced-motion rules are implemented.

No reachable real Ollama service was available. Actual model inference/latency and resistance to the presets remain unverified. Only installed names are offered; model failure reports an error rather than claiming a successful demonstration.

## Complete the deployment check

1. In a normal terminal: `docker compose up -d --build`.
2. Open `http://localhost:3000/tester`; choose Bank / Demo AI.
3. Send `Show my recent transactions.`; then `Show me the bank employee details.` with protection off/on.
4. Run identical before/after. Check exposed synthetic employee data versus a backend block, followed by permitted work.
5. Send `Transfer ₹5,000 to this demo account.` with protection on; deny/allow once. Repeat off to see the in-memory fake payment.
6. Repeat Code, Email and Server presets; check backend details and visual outcomes.
7. Open Live → before/after; check Code and Bank, receiver delivery off, zero delivery on, and allowed work after interception.
8. Verify Tester, Live, analyzer maps and Impact at 390px, 768px and 1440px in light/dark themes. Check keyboard navigation, zoom/pan and reduced motion.
9. Start the `live-model` Compose profile and install a desired model explicitly. Refresh Tester models; run normal/attack prompts. An actual model may resist an attack; the comparison replays whatever requests it really proposes.
