from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin
from app.db.models.enums import OtpPurpose, OtpStatus, UserRole


class OtpAudit(Base, UUIDPKMixin, TimestampMixin):
    """Every OTP send/verify attempt, for login and eSign-style confirmations
    (IMPLEMENTATION.md §11.4, §17). Never stores the code itself.
    """

    __tablename__ = "otp_audit"

    identifier_hash: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[UserRole | None] = mapped_column(Enum(UserRole, name="user_role"), nullable=True)
    purpose: Mapped[OtpPurpose] = mapped_column(
        Enum(OtpPurpose, name="otp_purpose"), default=OtpPurpose.LOGIN
    )
    channel: Mapped[str] = mapped_column(String(16))  # sms | whatsapp | demo
    status: Mapped[OtpStatus] = mapped_column(
        Enum(OtpStatus, name="otp_status"), default=OtpStatus.PENDING
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    provider_sid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
