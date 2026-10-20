"""Server-Sent Events stream (IMPLEMENTATION.md §3, §4.1): the notification
bell and live dashboards subscribe here. Phase P1 broadcasts every published
outbox event to every authenticated connection; per-recipient targeting
arrives with the notification orchestrator (Phase P7) by filtering on a
`recipient_user_id` the payload will carry — the frontend already treats each
message as "something changed, go refetch" rather than trusting the payload
shape, so that narrowing will be additive.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from app.core.deps import get_current_user
from app.core.redis_client import get_async_redis
from app.db.models.user import User

router = APIRouter(tags=["sse"])

CHANNEL = "acp.events"


@router.get("/stream")
async def stream(request: Request, user: User = Depends(get_current_user)) -> EventSourceResponse:
    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        redis = get_async_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(CHANNEL)
        try:
            yield {"event": "connected", "data": json.dumps({"user_id": str(user.id)})}
            while True:
                if await request.is_disconnected():
                    break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
                if message is not None:
                    yield {"event": "message", "data": message["data"]}
                else:
                    yield {"event": "ping", "data": "{}"}
        finally:
            await pubsub.unsubscribe(CHANNEL)
            await pubsub.aclose()  # type: ignore[no-untyped-call]

    return EventSourceResponse(event_generator())
