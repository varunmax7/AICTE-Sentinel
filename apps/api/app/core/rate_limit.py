"""Fixed-window Redis rate limiting (IMPLEMENTATION.md §17: OTP send 3/10min
per identifier, public endpoints 30/min per IP). Good enough for throttling —
not a precision rate limiter.
"""

from __future__ import annotations

from app.core.redis_client import get_redis


def check_and_increment(key: str, *, limit: int, window_seconds: int) -> bool:
    """Increments the counter for `key` and returns True if still within
    `limit` for this window, False if the limit was already reached.
    """
    client = get_redis()
    # redis-py's stubs type incr()/get() generically over the sync/async split,
    # so mypy sees `Awaitable[Any] | Any` for the sync client's return value.
    count = int(client.incr(key))  # type: ignore[arg-type]
    if count == 1:
        client.expire(key, window_seconds)
    return count <= limit
