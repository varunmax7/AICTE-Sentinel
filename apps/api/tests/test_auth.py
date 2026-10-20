from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import encrypt_field, hash_identifier
from app.db.models.audit import AuditEvent
from app.db.models.enums import UserRole
from app.db.models.user import User
from app.db.session import SessionLocal

PHONE = "+911234500000"
DEMO_OTP = "123456"


async def _create_user(role: UserRole) -> None:
    async with SessionLocal() as db:
        db.add(
            User(
                role=role,
                name="Test User",
                phone_enc=encrypt_field(PHONE),
                phone_hash=hash_identifier(PHONE),
            )
        )
        await db.commit()


async def test_otp_login_flow_sets_cookies_and_me_works(client: AsyncClient) -> None:
    await _create_user(UserRole.ADMIN)

    send_resp = await client.post(
        "/api/v1/auth/otp/send", json={"identifier": PHONE, "role": "ADMIN"}
    )
    assert send_resp.status_code == 200
    assert send_resp.json()["sent"] is True

    verify_resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"identifier": PHONE, "role": "ADMIN", "code": DEMO_OTP},
    )
    assert verify_resp.status_code == 200
    body = verify_resp.json()
    assert body["role"] == "ADMIN"
    assert "acp_access" in client.cookies
    assert "acp_refresh" in client.cookies

    me_resp = await client.get("/api/v1/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["id"] == body["id"]


async def test_login_writes_audit_event(client: AsyncClient) -> None:
    await _create_user(UserRole.SCRUTINY_OFFICER)
    await client.post(
        "/api/v1/auth/otp/send", json={"identifier": PHONE, "role": "SCRUTINY_OFFICER"}
    )
    await client.post(
        "/api/v1/auth/otp/verify",
        json={"identifier": PHONE, "role": "SCRUTINY_OFFICER", "code": DEMO_OTP},
    )

    async with SessionLocal() as db:
        result = await db.execute(select(AuditEvent).where(AuditEvent.action == "auth.login"))
        events = result.scalars().all()
        assert len(events) == 1
        assert events[0].entity_type == "user"
        assert events[0].hash


async def test_otp_verify_wrong_code_is_rejected(client: AsyncClient) -> None:
    await _create_user(UserRole.SCRUTINY_OFFICER)
    await client.post(
        "/api/v1/auth/otp/send", json={"identifier": PHONE, "role": "SCRUTINY_OFFICER"}
    )
    resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"identifier": PHONE, "role": "SCRUTINY_OFFICER", "code": "000000"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_OTP"


async def test_public_role_cannot_request_otp(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/otp/send", json={"identifier": PHONE, "role": "PUBLIC"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "ROLE_NOT_LOGINABLE"


async def test_unknown_account_returns_404(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/otp/send", json={"identifier": "+919999999999", "role": "ADMIN"}
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


async def test_me_without_cookie_is_401(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401


async def test_me_patch_updates_preferred_language(client: AsyncClient) -> None:
    await _create_user(UserRole.ADMIN)
    await client.post("/api/v1/auth/otp/send", json={"identifier": PHONE, "role": "ADMIN"})
    await client.post(
        "/api/v1/auth/otp/verify", json={"identifier": PHONE, "role": "ADMIN", "code": DEMO_OTP}
    )

    resp = await client.patch("/api/v1/me", json={"preferred_language": "hi"})
    assert resp.status_code == 200
    assert resp.json()["preferred_language"] == "hi"
