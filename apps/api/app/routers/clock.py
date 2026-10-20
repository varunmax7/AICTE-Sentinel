"""IMPLEMENTATION.md §18.1 — the frontend reads server time from here (and via
SSE deltas later) for SLA badges; it must never trust the browser clock, since
`DEMO_MODE` time travel only moves the server clock.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core import clock
from app.core.config import get_settings

router = APIRouter(tags=["clock"])


@router.get("/clock")
def get_clock() -> dict[str, object]:
    settings = get_settings()
    return {
        "now": clock.now().isoformat(),
        "demo_mode": settings.DEMO_MODE,
        "offset_seconds": clock.get_offset_seconds() if settings.DEMO_MODE else 0,
    }
