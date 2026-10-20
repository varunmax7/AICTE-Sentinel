"""Demo-aware clock (IMPLEMENTATION.md §18.1). All backend "now" calls go
through this module — never `datetime.now()` directly — so the demo panel's
time travel (Phase P12) can fast-forward the whole system and the deadline
scanner (Phase P7) reacts immediately.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import redis as redis_sync

from app.core.config import get_settings
from app.core.redis_client import get_redis

IST = ZoneInfo("Asia/Kolkata")
OFFSET_KEY = "demo:clock_offset_seconds"


def now() -> datetime:
    settings = get_settings()
    real = datetime.now(tz=IST)
    if not settings.DEMO_MODE:
        return real
    try:
        # See app.core.rate_limit for why the `type: ignore` is needed here.
        offset = int(get_redis().get(OFFSET_KEY) or 0)  # type: ignore[arg-type]
    except redis_sync.RedisError:
        offset = 0
    return real + timedelta(seconds=offset)


def set_offset_seconds(seconds: int) -> None:
    get_redis().set(OFFSET_KEY, seconds)


def get_offset_seconds() -> int:
    try:
        return int(get_redis().get(OFFSET_KEY) or 0)  # type: ignore[arg-type]
    except redis_sync.RedisError:
        return 0


def reset_offset() -> None:
    get_redis().delete(OFFSET_KEY)
