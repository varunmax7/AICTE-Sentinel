"""FastAPI entrypoint for the AICTE ACP core API (`apps/api`).

Phase P0 ships only the health endpoint and settings wiring — see
IMPLEMENTATION.md §19 Phase P0. Routers for auth, applications, documents,
etc. are mounted here starting Phase P1.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AICTE Approval & Compliance Portal — Core API",
    version="0.1.0",
)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.APP_ENV}
