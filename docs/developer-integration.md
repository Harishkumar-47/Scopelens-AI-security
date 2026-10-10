# Python tool gateway integration

ScopeLens executes a small set of real local sandbox file reads and in-memory synthetic tools. The Python middleware uses the same deterministic gateway as Live and Tester. It does not execute arbitrary host tools and does not automatically protect an agent's other tool paths.

Start the backend, then run:

```bash
python3 examples/scopelens_sdk.py
```

Expected: `ALLOW` for the project file and `BLOCK` for synthetic credentials. Inspect **Proof** for the matching execution evidence.

For an agent, replace its direct tool calls with `gateway.call(tool, target)`. The SDK returns permitted file content only after execution. A denial returns no content. Do not execute the original tool a second time after this call: the gateway already executed the permitted sandbox tool.

```python
from examples.scopelens_sdk import ScopeLens

gateway = ScopeLens({
    "job": "Review project",
    "tools": ["read_file"],
    "resources": ["/workspace/github-project/**"],
    "forbidden": ["/secrets/**"],
    "approval_tools": [],
    "delegates": ["reviewer"],
})
result = gateway.call("read_file", "/workspace/github-project/app.py")
```

`POST /api/gateway/sessions` returns a session ID and owner bearer token once. Keep the token private. Tool execution, delegation, and approval routes require `Authorization: Bearer TOKEN`. Tokens are intentionally not included in list endpoints or audit exports.

Policy fields: `job`, `tools`, `resources`, `forbidden`, `approval_tools`, `warn_tools`, `delegates`. Resource rules support exact sandbox paths and trailing `/**` subtree scopes. Intent Lock can narrow the sandbox policy; it cannot override hard sandbox blocks or waive payment approval.

Use `POST /api/gateway/sessions/{id}/delegate` with `{ "name": "reviewer", "policy": {...} }` to create a child. Its tools and resource scopes must be subsets of the parent. It inherits forbidden resources, approvals, and warnings. Its own delegation list is intersected with the parent's grant.

Approvals expire after 120 seconds and are consumed on either approval or denial. An expired or reused ID returns 404. A policy decision of ASK has not executed the action. Restarting the backend invalidates active sessions and approvals; redacted session history and evidence remain in SQLite.

This is a single-operator local deployment. There is no multi-tenant identity system. Provider permission imports (MCP, OAuth, GitHub, AWS, Azure, GCP) remain simplified analysis adapters, not production runtime enforcement integrations. Arbitrary Python callback/host filesystem tooling and MCP proxy deployment remain future work.
