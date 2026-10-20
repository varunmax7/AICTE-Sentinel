"""Generic OTP confirmation for state-changing actions beyond login — e.g.
`POST /applications/{id}/submit` (§13.2 "OTP required"), and later the
committee decision (P5) and compliance verification (P6) endpoints that need
the same "send → verify" shape against the *acting user's own phone* rather
than an arbitrary identifier+role pair.

Reuses `otp_audit` (already carries an `OtpPurpose.ESIGN` member from Phase
P1 — see docs/DECISIONS.md) instead of a new table: identical shape to the
login flow in `app.routers.auth`, keyed by the user's own `phone_hash` +
`role` + `purpose` rather than a request-supplied identifier.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.config import get_settings
from app.core.security import decrypt_field
from app.db.models.enums import OtpPurpose, OtpStatus
from app.db.models.otp import OtpAudit
from app.db.models.user import User
from app.services.auth.otp import OtpProvider

OTP_VERIFY_MAX_ATTEMPTS = 5


async def send_action_otp(db: AsyncSession, user: User, *, purpose: OtpPurpose) -> None:
    settings = get_settings()
    identifier = decrypt_field(user.phone_enc) if user.phone_enc else None
    provider_sid = await OtpProvider(settings).send(identifier or "")

    db.add(
        OtpAudit(
            identifier_hash=user.phone_hash or "",
            role=user.role,
            purpose=purpose,
            channel="demo" if settings.DEMO_MODE else "sms",
            status=OtpStatus.PENDING,
            provider_sid=provider_sid,
            requested_at=clock.now(),
        )
    )
    await db.commit()


async def verify_action_otp(
    db: AsyncSession, user: User, *, purpose: OtpPurpose, code: str
) -> bool:
    settings = get_settings()
    result = await db.execute(
        select(OtpAudit)
        .where(
            OtpAudit.identifier_hash == (user.phone_hash or ""),
            OtpAudit.purpose == purpose,
            OtpAudit.status == OtpStatus.PENDING,
        )
        .order_by(OtpAudit.requested_at.desc())
        .limit(1)
    )
    otp_row = result.scalar_one_or_none()
    if otp_row is None:
        return False
    if otp_row.attempt_count >= OTP_VERIFY_MAX_ATTEMPTS:
        otp_row.status = OtpStatus.FAILED
        await db.commit()
        return False

    identifier = decrypt_field(user.phone_enc) if user.phone_enc else ""
    ok = await OtpProvider(settings).check(identifier, code)
    otp_row.attempt_count += 1
    if ok:
        otp_row.status = OtpStatus.VERIFIED
        otp_row.verified_at = clock.now()
    elif otp_row.attempt_count >= OTP_VERIFY_MAX_ATTEMPTS:
        otp_row.status = OtpStatus.FAILED
    await db.commit()
    return ok
