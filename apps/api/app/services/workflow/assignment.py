"""Workload balancer (IMPLEMENTATION.md §9.5): on activating a HUMAN stage,
pick the user with that stage's role in the application's region minimising
`weighted_load = Σ(active cases) + overdue × 3`. Ties break on user id — a
stable, deterministic approximation of round-robin that's simple enough for
the Phase P2 seed data's scale (good enough for a demo-sized region; a real
rotation counter can replace this later without changing the call shape).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import now
from app.db.models.deadline import Deadline
from app.db.models.enums import StageStatus, UserRole
from app.db.models.user import User, UserRegion
from app.db.models.workflow import Assignment, StageInstance


async def _candidates(db: AsyncSession, *, role: UserRole, region_id: uuid.UUID) -> list[User]:
    result = await db.execute(
        select(User)
        .join(UserRegion, UserRegion.user_id == User.id)
        .where(User.role == role, User.is_active.is_(True), UserRegion.region_id == region_id)
        .order_by(User.id)
    )
    return list(result.scalars().all())


async def _weighted_load(db: AsyncSession, *, user_id: uuid.UUID, reference: datetime) -> float:
    result = await db.execute(
        select(StageInstance.id, Deadline.due_at)
        .outerjoin(Deadline, Deadline.id == StageInstance.deadline_id)
        .where(
            StageInstance.assigned_user_id == user_id, StageInstance.status == StageStatus.ACTIVE
        )
    )
    rows = result.all()
    load = float(len(rows))
    for _stage_id, due_at in rows:
        if due_at is not None and due_at < reference:
            load += 3.0
    return load


async def pick_assignee(db: AsyncSession, *, role: UserRole, region_id: uuid.UUID) -> User | None:
    candidates = await _candidates(db, role=role, region_id=region_id)
    if not candidates:
        return None
    reference = now()
    scored = [(await _weighted_load(db, user_id=u.id, reference=reference), u) for u in candidates]
    scored.sort(key=lambda pair: (pair[0], str(pair[1].id)))
    return scored[0][1]


async def assign(
    db: AsyncSession,
    stage_instance: StageInstance,
    user: User,
    *,
    assigned_by_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> Assignment:
    existing = await db.execute(
        select(Assignment).where(
            Assignment.stage_instance_id == stage_instance.id, Assignment.active.is_(True)
        )
    )
    for row in existing.scalars():
        row.active = False

    assignment = Assignment(
        stage_instance_id=stage_instance.id,
        user_id=user.id,
        assigned_by_user_id=assigned_by_user_id,
        reason=reason,
        active=True,
        at=now(),
    )
    db.add(assignment)
    stage_instance.assigned_user_id = user.id
    await db.flush()
    return assignment
