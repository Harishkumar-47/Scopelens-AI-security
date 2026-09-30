# Architecture

The backend accepts an agent configuration and passes it through a provider adapter. Adapters yield permission strings. The normalizer maps known strings to one of 29 capabilities and marks unknown permissions explicitly. NetworkX builds a directed graph of agent → permission → capability → resource/risk outcome. Risk rules inspect the normalized capability set. Scores derive from capability and risk weights. Simulation removes one permission and reruns the full pipeline.

The frontend uses React Router for pages and Cytoscape for graph exploration. The frontend proxies `/api` through nginx in Docker. There is no database in the MVP; browser session storage keeps the current analysis and comparison. API keys remain server-side.

AI explanations receive only the already computed findings and cannot alter severity or graph edges. A deterministic template is returned if disabled or unavailable.

## Runtime layer

The Live Lab uses a separate `backend/app/runtime` package. An optional local Ollama model can propose a limited JSON tool request. Replay mode emits the same request sequence without a model. Both paths enter `tool_gateway.py`, then `policy_engine.py` returns ALLOW, ASK or BLOCK. Only the gateway can read files from a fixed allowlist in `runtime/sandbox`; no host path, shell, external network destination or real payment API is available. Approved payment execution only appends a fake record to memory.

`activity_monitor.py` turns requests into events, a Scope Deviation Score and a resource graph. WebSockets stream complete session snapshots to the UI. The UI also polls as a connection fallback. Runtime sessions and approvals exist only in backend memory.
