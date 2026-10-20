"""Auth endpoints (IMPLEMENTATION.md §13.1): OTP login via Twilio Verify (with
a `DEMO_MODE` fixed-code bypass) and JWT httpOnly cookies. `/me` lives in
`app.routers.me` since it isn't under the `/auth` prefix in §13.1.

Login identifier is always a phone number matched against `users.phone_hash`
— `institution_contacts` is a separate notification-targeting concept, not a
login table (see docs/DECISIONS.md). `PUBLIC` has no login and `FACULTY` uses
its own `/faculty/otp/*` endpoints (§13.12), so neither role is accepted here.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.config import Settings, get_settings
from app.core.deps import user_region_ids
from app.core.rate_limit import check_and_increment
from app.core.security import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    access_cookie_max_age,
    create_token,
    decode_token,
    hash_identifier,
    refresh_cookie_max_age,
)
from app.db.models.enums import ActorType, OtpPurpose, OtpStatus, UserRole
from app.db.models.geo import Region
from app.db.models.otp import OtpAudit
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import MeOut, OtpSendRequest, OtpSendResponse, OtpVerifyRequest, RegionOut
from app.services.audit.chain import write_audit_event
from app.services.auth.otp import OtpProvider
from app.services.events import emit_event, trigger_publish

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_DISALLOWED_ROLES = {UserRole.PUBLIC, UserRole.FACULTY}
OTP_SEND_LIMIT = 3
OTP_SEND_WINDOW_SECONDS = 600
OTP_VERIFY_MAX_ATTEMPTS = 5


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _get_user(db: AsyncSession, *, identifier: str, role: UserRole) -> User | None:
    result = await db.execute(
        select(User).where(User.phone_hash == hash_identifier(identifier), User.role == role)
    )
    return result.scalar_one_or_none()


async def build_me(db: AsyncSession, user: User) -> MeOut:
    region_ids = await user_region_ids(db, user)
    regions: list[RegionOut] = []
    if region_ids:
        result = await db.execute(select(Region).where(Region.id.in_(region_ids)))
        regions = [RegionOut(id=str(r.id), code=r.code, name=r.name) for r in result.scalars()]
    return MeOut(
        id=str(user.id),
        name=user.name,
        role=user.role,
        preferred_language=user.preferred_language,
        theme=user.theme,
        institution_id=str(user.institution_id) if user.institution_id else None,
        regions=regions,
    )


def _set_auth_cookies(
    response: Response, *, access_token: str, refresh_token: str, settings: Settings
) -> None:
    secure = settings.APP_ENV != "development"
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=access_cookie_max_age(settings),
        httponly=True,
        secure=secure,
        samesite="lax",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=refresh_cookie_max_age(settings),
        httponly=True,
        secure=secure,
        samesite="lax",
    )


@router.post("/otp/send", response_model=OtpSendResponse)
async def send_otp(
    body: OtpSendRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> OtpSendResponse:
    if body.role in LOGIN_DISALLOWED_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "ROLE_NOT_LOGINABLE"})

    identifier_hash = hash_identifier(body.identifier)
    if not check_and_increment(
        f"otp_send:{identifier_hash}", limit=OTP_SEND_LIMIT, window_seconds=OTP_SEND_WINDOW_SECONDS
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail={"code": "RATE_LIMITED"})

    user = await _get_user(db, identifier=body.identifier, role=body.role)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "ACCOUNT_NOT_FOUND"})

    settings = get_settings()
    provider_sid = await OtpProvider(settings).send(body.identifier)

    db.add(
        OtpAudit(
            identifier_hash=identifier_hash,
            role=body.role,
            purpose=OtpPurpose.LOGIN,
            channel="demo" if settings.DEMO_MODE else "sms",
            status=OtpStatus.PENDING,
            provider_sid=provider_sid,
            requested_at=clock.now(),
            ip=_client_ip(request),
        )
    )
    await db.commit()

    return OtpSendResponse(sent=True, expires_in_seconds=OTP_SEND_WINDOW_SECONDS)


@router.post("/otp/verify", response_model=MeOut)
async def verify_otp(
    body: OtpVerifyRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MeOut:
    if body.role in LOGIN_DISALLOWED_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "ROLE_NOT_LOGINABLE"})

    identifier_hash = hash_identifier(body.identifier)
    result = await db.execute(
        select(OtpAudit)
        .where(
            OtpAudit.identifier_hash == identifier_hash,
            OtpAudit.role == body.role,
            OtpAudit.status == OtpStatus.PENDING,
        )
        .order_by(OtpAudit.requested_at.desc())
        .limit(1)
    )
    otp_row = result.scalar_one_or_none()
    if otp_row is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "OTP_NOT_REQUESTED"})

    if otp_row.attempt_count >= OTP_VERIFY_MAX_ATTEMPTS:
        otp_row.status = OtpStatus.FAILED
        await db.commit()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail={"code": "TOO_MANY_ATTEMPTS"})

    settings = get_settings()
    ok = await OtpProvider(settings).check(body.identifier, body.code)
    otp_row.attempt_count += 1
    if not ok:
        if otp_row.attempt_count >= OTP_VERIFY_MAX_ATTEMPTS:
            otp_row.status = OtpStatus.FAILED
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_OTP"})

    user = await _get_user(db, identifier=body.identifier, role=body.role)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "ACCOUNT_NOT_FOUND"})

    otp_row.status = OtpStatus.VERIFIED
    otp_row.verified_at = clock.now()
    user.last_login_at = clock.now()

    await write_audit_event(
        db,
        actor_type=ActorType.USER,
        actor_id=str(user.id),
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        channel="otp",
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await emit_event(db, "auth.login", {"user_id": str(user.id), "role": user.role.value})

    await db.commit()
    trigger_publish()

    access_token = create_token(
        user_id=str(user.id), role=user.role.value, token_type="access", settings=settings
    )
    refresh_token = create_token(
        user_id=str(user.id), role=user.role.value, token_type="refresh", settings=settings
    )
    _set_auth_cookies(
        response, access_token=access_token, refresh_token=refresh_token, settings=settings
    )

    return await build_me(db, user)


@router.post("/refresh")
async def refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> dict[str, bool]:
    settings = get_settings()
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "NOT_AUTHENTICATED"})

    try:
        payload = decode_token(refresh_token, settings=settings)
    except Exception as exc:  # noqa: BLE001 - any decode failure is "not authenticated"
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_TOKEN"}) from exc
    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_TOKEN_TYPE"})

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "USER_NOT_FOUND"})

    access_token = create_token(
        user_id=str(user.id), role=user.role.value, token_type="access", settings=settings
    )
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=access_cookie_max_age(settings),
        httponly=True,
        secure=settings.APP_ENV != "development",
        samesite="lax",
    )
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(ACCESS_COOKIE)
    response.delete_cookie(REFRESH_COOKIE)
    return {"ok": True}
