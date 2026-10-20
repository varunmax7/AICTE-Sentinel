"""Unified deadline timer (IMPLEMENTATION.md §10.1, §21) and the holiday
calendar the working-day calculator reads. The full reminder/escalation
ladder (`escalation_policies`, `escalations`, `next_step_at` stepping) is
Phase P7 scope — Phase P2 only needs create/pause/resume/close.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin
from app.db.models.enums import DeadlineOwnerParty, DeadlineStatus


class Deadline(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "deadlines"

    subject_type: Mapped[str] = mapped_column(String(32))
    subject_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True))
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("applications.id"), nullable=True
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[DeadlineStatus] = mapped_column(
        Enum(DeadlineStatus, name="deadline_status"), default=DeadlineStatus.ACTIVE
    )
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_total_seconds: Mapped[int] = mapped_column(Integer, default=0)
    policy_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_step_index: Mapped[int] = mapped_column(Integer, default=-1)
    next_step_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_party: Mapped[DeadlineOwnerParty] = mapped_column(
        Enum(DeadlineOwnerParty, name="deadline_owner_party"), default=DeadlineOwnerParty.OFFICER
    )
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Holiday(Base):
    __tablename__ = "holidays"

    date: Mapped[date] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    region_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regions.id"), nullable=True)
