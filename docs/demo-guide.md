# Hackathon demo

## Primary: Live Agent Lab

1. Run `docker compose up --build` and open `http://localhost:3000/live`.
2. Show Code Assistant, project-only scope, Demo Replay Mode and the **SANDBOX DEMONSTRATION** banner.
3. Keep **Unprotected** selected and click **Run agent task**. The agent reads project files, consumes an untrusted synthetic issue, reads fake credentials, and sends only to the in-memory local demo sink. Show the red graph and **SIMULATED DATA EXPOSURE** alert.
4. Switch to **Protected**, which creates a fresh session. Run the same task. The secret read and local send are blocked; the agent then reads the project README. Show **CORE TASK STILL WORKING**.
5. Open **View live comparison**. Show the same task and replay model on both sides, with exposure dropping to zero and blocked actions appearing.
6. Optionally select **Finance demo**, prepare a fake payment, request execution, and click **Deny** in the one-time approval modal. No payment is created.

## Pre-deployment analyzer

1. Open **Scenarios**, select Support Agent, and analyze its five permissions.
2. Show the capability graph, three risk chains and 76 HIGH ScopeLens Exposure Score.
3. Simulate removing `email.send_external`. The score becomes 28 LOW and risk chains drop to zero.
4. Open the existing before/after comparison page.

Health check: `curl http://localhost:8000/api/health`. API docs: `http://localhost:8000/docs`.

All data, files, credentials and payments in the Live Lab are fake. No Internet destination receives data.
