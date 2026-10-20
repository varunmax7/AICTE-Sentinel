"""Domain-event emission into the transactional outbox (IMPLEMENTATION.md §4.1).

Write the outbox row in the *same* transaction as the business change, commit,
then call `trigger_publish()` to nudge a Celery worker to publish it to Redis
pub/sub immediately. If the broker is briefly unavailable, `trigger_publish`
fails soft — Celery Beat's `publish_pending` runs every few seconds as a
safety net (see `app/workers/beat_schedule.py`), so no event is silently lost,
only delayed.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.outbox import OutboxEvent

logger = logging.getLogger(__name__)


async def emit_event(db: AsyncSession, event: str, payload: dict[str, Any]) -> OutboxEvent:
    row = OutboxEvent(event=event, payload=payload)
    db.add(row)
    await db.flush()
    return row


def trigger_publish() -> None:
    from app.workers.celery_app import celery_app

    try:
        celery_app.send_task("app.workers.tasks.outbox.publish_pending")
    except Exception:  # noqa: BLE001 - best-effort nudge; beat is the safety net
        logger.warning(
            "Could not enqueue outbox publish task; beat will pick it up.", exc_info=True
        )
