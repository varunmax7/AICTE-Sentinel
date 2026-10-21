"""FastAPI entrypoint for the AICTE ACP core API (`apps/api`).

Phase P1 added auth (OTP + JWT cookies), `/me`, the demo clock, and the SSE
stream. Phase P2 added the workflow engine's applications/stages endpoints.
Phase P3 adds document upload/extraction/verification and the application
pre-scrutiny AI report — see IMPLEMENTATION.md §19 Phase P3.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.routers import (
    application_types,
    applications,
    auth,
    clock,
    documents,
    institutions,
    me,
    sse,
    stages,
)
from app.services.storage import ensure_bucket

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    ensure_bucket()
    yield


app = FastAPI(
    title="AICTE Approval & Compliance Portal — Core API",
    version="0.1.0",
    lifespan=lifespan,
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
app.include_router(documents.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.APP_ENV}
