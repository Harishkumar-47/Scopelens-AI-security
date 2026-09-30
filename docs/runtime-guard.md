# Live Lab security boundary

All demo files are synthetic and committed under `backend/app/runtime/sandbox`. File execution is restricted to a fixed path allowlist. The gateway rejects traversal, host paths, symlinks escaping the sandbox, and conceptual Windows paths. No shell tool or arbitrary HTTP send tool is available. `demo_send` only appends a byte count and classification to an in-memory local sink.

The coding agent's declared scope is `/workspace/github-project/**`. The issue file is tagged UNTRUSTED. After reading it, replay mode requests `/secrets/demo_credentials.txt` and then `demo_send`. In unprotected mode, the fake secret is read and a simulated exposure is recorded. In protected mode, the read is blocked before the file is opened and the send is also blocked. The agent can still read the project README afterward.

The optional Ollama adapter can propose only `read_file`, `demo_send`, or `finish`. It cannot run tools. The same deterministic policy decides every proposed request. If Ollama fails, the app labels and uses Demo Replay Mode.

Finance mode reads a fake invoice, previews and prepares a fake payment. Every `payment.execute` request enters ASK, and only a one-time human approval creates a synthetic payment record. DENY creates no payment. There is no real financial integration.

Resource classes are NORMAL, USER_DATA, SENSITIVE, SECRET, FINANCIAL, SYSTEM and OUT_OF_SCOPE. Cross-platform path patterns are classified for risk understanding; only allowlisted Linux-style sandbox paths are executable. Scope Deviation Score is a ScopeLens prototype metric based on attempted movements, not an industry standard.
