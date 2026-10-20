"""Hash-chained audit trail (IMPLEMENTATION.md §16).

`write_audit_event` must be called inside the same DB transaction as the
business change it documents (§0.2 rule 5) — it flushes but does not commit;
the caller commits. `verify_chain` recomputes the whole chain from scratch
and reports the first row where either the row's own hash or its recorded
`prev_hash` no longer matches, which is how `/audit/verify` detects tampering.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import now
from app.db.models.audit import AuditEvent
from app.db.models.enums import ActorType

ADVISORY_LOCK_KEY = 42


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        # Normalize to UTC before formatting: a freshly-written event's
        # `occurred_at` carries clock.now()'s IST tzinfo, but reading the same
        # TIMESTAMPTZ value back from Postgres returns it in UTC — same
        # instant, different offset in the string unless both sides agree on
        # one timezone first. Without this, `verify_chain` would recompute a
        # different hash for every row it re-reads from the DB.
        return value.astimezone(UTC).isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    raise TypeError(f"Object of type {type(value)} is not JSON serializable")


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, default=_json_default, separators=(",", ":"))


def _hashable_payload(event: AuditEvent) -> dict[str, Any]:
    actor_type = event.actor_type
    return {
        "occurred_at": event.occurred_at,
        "actor_type": actor_type.value if isinstance(actor_type, ActorType) else actor_type,
        "actor_id": event.actor_id,
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "before": event.before,
        "after": event.after,
        "reason": event.reason,
    }


def _compute_hash(prev_hash: str | None, event: AuditEvent) -> str:
    digest_input = (prev_hash or "") + _canonical_json(_hashable_payload(event))
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()


async def _last_hash(db: AsyncSession) -> str | None:
    result = await db.execute(select(AuditEvent.hash).order_by(AuditEvent.id.desc()).limit(1))
    return result.scalar_one_or_none()


async def write_audit_event(
    db: AsyncSession,
    *,
    actor_type: ActorType,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    application_id: uuid.UUID | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    channel: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AuditEvent:
    # Serializes concurrent writers onto one chain for the lifetime of this transaction.
    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADVISORY_LOCK_KEY})

    prev_hash = await _last_hash(db)

    event = AuditEvent(
        occurred_at=now(),
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        application_id=application_id,
        before=before,
        after=after,
        reason=reason,
        channel=channel,
        ip=ip,
        user_agent=user_agent,
        prev_hash=prev_hash,
        hash="",
    )
    event.hash = _compute_hash(prev_hash, event)

    db.add(event)
    await db.flush()
    return event


async def verify_chain(db: AsyncSession) -> tuple[bool, int | None]:
    result = await db.execute(select(AuditEvent).order_by(AuditEvent.id.asc()))
    prev_hash: str | None = None
    for row in result.scalars():
        if row.prev_hash != prev_hash or row.hash != _compute_hash(prev_hash, row):
            return False, row.id
        prev_hash = row.hash
    return True, None
