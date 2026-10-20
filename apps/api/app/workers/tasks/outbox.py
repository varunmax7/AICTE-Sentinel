"""Publishes unpublished `outbox_events` rows to the Redis `acp.events`
pub/sub channel (IMPLEMENTATION.md §4.1). Run both on-demand (nudged by
`app.services.events.trigger_publish` right after a commit) and on a beat
schedule as a safety net for anything the nudge missed.
"""

from __future__ import annotations

import asyncio
import json

from sqlalchemy import select

from app.core.redis_client import get_redis
from app.db.models.outbox import OutboxEvent
from app.db.session import SessionLocal
from app.workers.celery_app import celery_app

CHANNEL = "acp.events"


@celery_app.task(name="app.workers.tasks.outbox.publish_pending")
def publish_pending() -> int:
    return asyncio.run(_publish_pending_async())


async def _publish_pending_async() -> int:
    async with SessionLocal() as db:
        result = await db.execute(
            select(OutboxEvent)
            .where(OutboxEvent.published.is_(False))
            .order_by(OutboxEvent.at.asc())
            .limit(500)
        )
        rows = list(result.scalars())
        if not rows:
            return 0

        redis = get_redis()
        for row in rows:
            redis.publish(
                CHANNEL,
                json.dumps({"event": row.event, "payload": row.payload, "at": row.at.isoformat()}),
            )
            row.published = True
        await db.commit()
        return len(rows)
