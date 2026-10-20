"""Shared Redis clients. One sync client (clock, rate limiting — simple,
low-latency, local calls) and one async client (SSE pub/sub, which needs to
await on `pubsub.get_message` without blocking the event loop).
"""

from __future__ import annotations

import redis as redis_sync
import redis.asyncio as redis_async

from app.core.config import get_settings

_sync_client: redis_sync.Redis | None = None
_async_client: redis_async.Redis | None = None


def get_redis() -> redis_sync.Redis:
    global _sync_client
    if _sync_client is None:
        _sync_client = redis_sync.Redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _sync_client


def get_async_redis() -> redis_async.Redis:
    global _async_client
    if _async_client is None:
        _async_client = redis_async.Redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _async_client
