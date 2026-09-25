"""The DRISHTI engine: every route lives under /api/v1.

Vercel keeps the original request path when it routes into this service, so the
prefix is part of each route rather than stripped by a rewrite.
"""

from fastapi import FastAPI

app = FastAPI(title="DRISHTI engine", version="0.1.0", docs_url="/api/v1/docs",
              openapi_url="/api/v1/openapi.json")


@app.get("/api/v1/health")
def health() -> dict:
    return {"ok": True, "service": "drishti-engine"}
