from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPKMixin


class OutboxEvent(Base, UUIDPKMixin):
    """Transactional outbox (IMPLEMENTATION.md §4.1). Written in the same
    transaction as the domain change; `app.workers.tasks.outbox.publish_pending`
    publishes unpublished rows to the Redis `acp.events` channel.
    """

    __tablename__ = "outbox_events"

    event: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
