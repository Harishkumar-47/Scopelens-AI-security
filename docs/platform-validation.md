# ScopeLens validation record — 2026-10-09

These results are observations from this workspace, not a production security certification.

| Check | Observed result |
| --- | --- |
| Backend unit/API suite | 68 passed; includes allow/deny, traversal and internal symlinks, prompt-injection replay, payment approval/denial/expiry/reuse, owner authorization, email/server denial, delegation narrowing, persistent evidence/history, unknown/invalid model requests, timeout and disconnected-runtime handling |
| Frontend production build | TypeScript and Vite passed |
| Browser checks | 10 passed against the final Docker frontend across desktop Chromium and iPhone-sized Chromium; workflow/theme/overflow, Live replay, authenticated denial, Custom Intent Lock, Proof download, imported provider permissions |
| Python integration | Real project fixture read allowed; synthetic credential read blocked; protected state remained unchanged on denial |
| Frontend dependency audit | Zero known vulnerabilities after compatible source-map-js patch |
| Compose configuration | Validation passed; named audit/model volumes and loopback ports |
| Restart persistence | Same SQLite evidence and redacted session history IDs survived a backend restart; backend, audit and Qwen readiness passed afterwards |
| Final deployed API acceptance | Real Qwen inference and all gateway acceptance assertions passed with the CPU settings |

The first actual Docker API acceptance run passed real Qwen inference/tool-request handling, all four identical before/after sandbox comparisons, approval authorization/reuse, missing-model errors and redacted execution evidence. Qwen requested `read_file` for `/workspace/github-project/README.md`; the request was inferred, not scripted.

During concurrent Docker rebuilding, repeat cold-load checks exceeded the original 90-second limit. Ollama was still healthy; the application correctly reported failure instead of switching to Demo AI. A direct CPU test with two threads and a 1024-token context completed real generation, with a measured cold load of about 66.85 seconds. The normal adapter now uses two threads, a 128-token batch and 2048-token context, retains the model for 30 minutes, and bounds the configurable timeout to 15–300 seconds (default 240). After the final rebuild with these CPU settings, the actual deployed acceptance script passed real Qwen inference, all four sandbox comparisons, owner authorization/single-use payments, unavailable-model behavior and persistent redacted evidence.

Earlier browser failures identified a still-running older Docker API that supported only Code/Payments comparison. After the updated backend became healthy, all 10 checks passed. No mocked model test is counted as real Qwen inference.

## Practical limits

- File reads are real reads of synthetic fixtures. Payments, receiver deliveries and server deletion are in-memory simulations.
- The Python example connects an external local client to the sandbox gateway. It does not wrap arbitrary host callbacks or claim host-level protection.
- SQLite retains redacted history/evidence, not active prompt contexts or approvals. Original task content stays ephemeral; persistent reports include its fingerprint.
- Legitimate-task success means permitted sandbox access continued. It does not prove a code repair or real financial operation succeeded.
- Provider imports remain simplified analysis adapters. This local single-operator application has no production tenant identity, signed evidence or complete cloud semantics.
- CI configuration was added; local checks were run. A remote GitHub Actions run has not been claimed.
