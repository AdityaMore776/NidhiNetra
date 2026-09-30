# DRISHTI engine

Python 3.12 + FastAPI service: data validation, the agents, risk fusion and the REST API (`/api/v1`).

```bash
pip install -e . -r requirements-dev.txt
ruff check drishti tests && pytest -q          # 259 tests
DATABASE_URL=... DRISHTI_AUTH=dev uvicorn drishti.main:app --port 8000
```

API docs at `/api/v1/docs`. Structure, scoring maths, auth and schema: [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md).
Agents: [`docs/AGENT-CATALOG.md`](../../docs/AGENT-CATALOG.md).
