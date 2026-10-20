"""FastAPI entrypoint for the AICTE ACP core API (`apps/api`).

Phase P1 added auth (OTP + JWT cookies), `/me`, the demo clock, and the SSE
stream. Phase P2 adds the workflow engine's applications/stages endpoints —
see IMPLEMENTATION.md §19 Phase P2.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.routers import application_types, applications, auth, clock, institutions, me, sse, stages

settings = get_settings()

app = FastAPI(
    title="AICTE Approval & Compliance Portal — Core API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.PUBLIC_WEB_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

install_error_handlers(app)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")
app.include_router(clock.router, prefix="/api/v1")
app.include_router(sse.router, prefix="/api/v1")
app.include_router(application_types.router, prefix="/api/v1")
app.include_router(applications.router, prefix="/api/v1")
app.include_router(stages.router, prefix="/api/v1")
app.include_router(institutions.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.APP_ENV}
