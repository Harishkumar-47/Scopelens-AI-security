# Five-minute demo

1. Start with `docker compose up --build` and open `http://localhost:3000`.
2. Click **Try demo scenario** to load Support Agent. Show its five ordinary-looking permissions.
3. Click **Analyze blast radius**. Explain the graph, red risk nodes and 76 HIGH score.
4. Open **Sensitive Data Exfiltration** and show its path. Point to `email.send_external` as the recommended removal.
5. Click **Simulate removal**. The graph updates; the score becomes 28 LOW and risk chains drop to zero.
6. Click **View comparison**. The side-by-side page shows that external email is blocked while the core support task remains available.
7. Optionally show DevOps and Finance scenarios and the AI-disabled explanation fallback.

Health check: `curl http://localhost:8000/api/health`. Swagger: `http://localhost:8000/docs`.
