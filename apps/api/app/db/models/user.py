import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin
from app.db.models.enums import ThemePref, UserRole


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"))
    name: Mapped[str] = mapped_column(String(256))
    email_enc: Mapped[str | None] = mapped_column(String, nullable=True)
    email_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    phone_enc: Mapped[str | None] = mapped_column(String, nullable=True)
    phone_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True
    )
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")
    theme: Mapped[ThemePref] = mapped_column(
        Enum(ThemePref, name="theme_pref"), default=ThemePref.SYSTEM
    )
    voice_pin_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    regions: Mapped[list["UserRegion"]] = relationship(back_populates="user")
    settings: Mapped["UserSettings | None"] = relationship(back_populates="user", uselist=False)


class UserRegion(Base):
    __tablename__ = "user_regions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    region_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regions.id"), primary_key=True)

    user: Mapped["User"] = relationship(back_populates="regions")


class UserSettings(Base, TimestampMixin):
    """Notification-channel preferences, split out from `users` so the identity
    table stays small (IMPLEMENTATION.md §13.1 `/me` mentions "notification
    prefs, call opt-in/time" but §21 doesn't carve out a table for them —
    see docs/DECISIONS.md).
    """

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    email_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    whatsapp_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    call_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_call_time: Mapped[str | None] = mapped_column(String(32), nullable=True)

    user: Mapped["User"] = relationship(back_populates="settings")
