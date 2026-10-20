"""Working-day calculator for stage SLAs (IMPLEMENTATION.md §9.4 deadline
creation). Weekends (Sat/Sun) are never working days; `holidays` rows with a
matching `region_id`, plus national holidays (`region_id IS NULL`), are also
excluded.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.deadline import Holiday


async def _holiday_dates(db: AsyncSession, *, region_id: uuid.UUID | None) -> set[object]:
    result = await db.execute(
        select(Holiday.date).where((Holiday.region_id.is_(None)) | (Holiday.region_id == region_id))
    )
    return set(result.scalars())


def _add_working_days(start: datetime, days: int, holiday_dates: set[object]) -> datetime:
    if days <= 0:
        return start
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5 and current.date() not in holiday_dates:
            added += 1
    return current


async def due_at_for_sla(
    db: AsyncSession,
    *,
    start: datetime,
    sla_days: int,
    sla_calendar: str,
    region_id: uuid.UUID | None,
) -> datetime:
    if sla_calendar == "WORKING_DAYS":
        holiday_dates = await _holiday_dates(db, region_id=region_id)
        return _add_working_days(start, sla_days, holiday_dates)
    return start + timedelta(days=sla_days)
