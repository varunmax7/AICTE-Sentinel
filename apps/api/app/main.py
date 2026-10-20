"""FastAPI entrypoint for the AICTE ACP core API (`apps/api`).

Phase P1 adds auth (OTP + JWT cookies), `/me`, the demo clock, and the SSE
stream — see IMPLEMENTATION.md §19 Phase P1. Routers for applications,
documents, etc. are mounted here starting Phase P2.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.routers import auth, clock, me, sse

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


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.APP_ENV}
