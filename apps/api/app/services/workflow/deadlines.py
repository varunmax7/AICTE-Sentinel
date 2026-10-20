"""Generic deadline create/pause/resume/close (IMPLEMENTATION.md §10.1, §9.4).
The reminder/escalation ladder that steps `next_step_at` is Phase P7 — these
helpers only manage the timer's own lifecycle, which is all Phase P2 (stage
SLAs) needs.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import now
from app.db.models.deadline import Deadline
from app.db.models.enums import DeadlineOwnerParty, DeadlineStatus


async def create_deadline(
    db: AsyncSession,
    *,
    subject_type: str,
    subject_id: uuid.UUID,
    institution_id: uuid.UUID | None,
    application_id: uuid.UUID | None,
    due_at: datetime,
    policy_key: str | None,
    owner_party: DeadlineOwnerParty = DeadlineOwnerParty.OFFICER,
) -> Deadline:
    deadline = Deadline(
        subject_type=subject_type,
        subject_id=subject_id,
        institution_id=institution_id,
        application_id=application_id,
        due_at=due_at,
        status=DeadlineStatus.ACTIVE,
        policy_key=policy_key,
        owner_party=owner_party,
    )
    db.add(deadline)
    await db.flush()
    return deadline


def pause_deadline(deadline: Deadline, *, new_owner: DeadlineOwnerParty | None = None) -> None:
    if deadline.status != DeadlineStatus.ACTIVE:
        return
    deadline.status = DeadlineStatus.PAUSED
    deadline.paused_at = now()
    if new_owner is not None:
        deadline.owner_party = new_owner


def resume_deadline(deadline: Deadline, *, new_owner: DeadlineOwnerParty | None = None) -> None:
    if deadline.status != DeadlineStatus.PAUSED:
        return
    if deadline.paused_at is not None:
        elapsed = (now() - deadline.paused_at).total_seconds()
        deadline.paused_total_seconds += max(0, int(elapsed))
        deadline.due_at = deadline.due_at + (now() - deadline.paused_at)
    deadline.status = DeadlineStatus.ACTIVE
    deadline.paused_at = None
    if new_owner is not None:
        deadline.owner_party = new_owner


def close_deadline(deadline: Deadline) -> None:
    deadline.status = DeadlineStatus.CLOSED
