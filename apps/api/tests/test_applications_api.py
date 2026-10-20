"""HTTP-level test of the Phase P2 applications/stages API: an institution
drafts and submits an application (OTP-gated), it routes into SCRUTINY and
auto-assigns an officer, the officer sees it in `/queue` and clears it, and
the application timeline reflects every step.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from app.core.security import encrypt_field, hash_identifier
from app.db.models.enums import ApplicationType, InstitutionType, UserRole, WorkflowRuleStatus
from app.db.models.geo import Region, State
from app.db.models.institution import Institution
from app.db.models.user import User, UserRegion
from app.db.models.workflow import ApplicationTypeDef, WorkflowRule
from app.db.session import SessionLocal

DEMO_OTP = "123456"

_STAGES = [
    {
        "key": "AI_PRECHECK",
        "label_key": "x",
        "kind": "SYSTEM",
        "sla_days": 0,
        "auto_complete": True,
    },
    {
        "key": "SCRUTINY",
        "label_key": "x",
        "kind": "HUMAN",
        "role": "SCRUTINY_OFFICER",
        "sla_days": 15,
        "sla_calendar": "WORKING_DAYS",
        "actions": ["CLEAR", "RETURN", "REFER_SENIOR", "REQUEST_CLARIFICATION"],
        "max_returns": 2,
        "auto_advance_on_clear": True,
    },
]


async def _seed_fixtures() -> tuple[str, str, str]:
    """Returns (institution_user_phone, officer_phone, institution_id)."""

    institution_phone = f"+9199901{uuid.uuid4().int % 100000:05d}"
    officer_phone = f"+9199902{uuid.uuid4().int % 100000:05d}"

    async with SessionLocal() as db:
        region = Region(
            code=f"HYD-{uuid.uuid4().hex[:6]}", name="Hyderabad", office_city="Hyderabad"
        )
        db.add(region)
        await db.flush()
        state = State(code=f"TG-{uuid.uuid4().hex[:6]}", name="Telangana", region_id=region.id)
        db.add(state)
        await db.flush()
        institution = Institution(
            aicte_id=f"AICTE-{uuid.uuid4().hex[:8]}",
            name="API Test College",
            type=InstitutionType.GOVT,
            state_id=state.id,
            region_id=region.id,
            city="Hyderabad",
            address="Addr",
        )
        db.add(institution)
        await db.flush()

        institution_user = User(
            role=UserRole.INSTITUTION,
            name="Institution User",
            phone_enc=encrypt_field(institution_phone),
            phone_hash=hash_identifier(institution_phone),
            institution_id=institution.id,
        )
        db.add(institution_user)
        officer = User(
            role=UserRole.SCRUTINY_OFFICER,
            name="Scrutiny Officer",
            phone_enc=encrypt_field(officer_phone),
            phone_hash=hash_identifier(officer_phone),
        )
        db.add(officer)
        await db.flush()
        db.add(UserRegion(user_id=officer.id, region_id=region.id))

        rule = WorkflowRule(
            rule_key=f"EXTENSION_OF_APPROVAL@test@{uuid.uuid4().hex[:8]}",
            application_type=ApplicationType.EXTENSION_OF_APPROVAL,
            academic_year="2026-27",
            version=1,
            definition={
                "rule_id": "test",
                "application_type": "EXTENSION_OF_APPROVAL",
                "academic_year": "2026-27",
                "version": 1,
                "stages": _STAGES,
                "branches": [],
            },
            status=WorkflowRuleStatus.PUBLISHED,
        )
        db.add(rule)
        await db.flush()
        db.add(
            ApplicationTypeDef(
                code=ApplicationType.EXTENSION_OF_APPROVAL,
                name_key="x",
                required_document_types=[],
                default_rule_id=rule.id,
            )
        )
        institution_id = str(institution.id)
        await db.commit()

    return institution_phone, officer_phone, institution_id


async def _login(client: AsyncClient, *, identifier: str, role: str) -> None:
    await client.post("/api/v1/auth/otp/send", json={"identifier": identifier, "role": role})
    resp = await client.post(
        "/api/v1/auth/otp/verify", json={"identifier": identifier, "role": role, "code": DEMO_OTP}
    )
    assert resp.status_code == 200


async def test_submit_route_queue_and_clear_end_to_end(client: AsyncClient) -> None:
    institution_phone, officer_phone, _institution_id = await _seed_fixtures()

    await _login(client, identifier=institution_phone, role="INSTITUTION")

    create_resp = await client.post(
        "/api/v1/applications",
        json={
            "application_type": "EXTENSION_OF_APPROVAL",
            "academic_year": "2026-27",
            "payload": {},
        },
    )
    assert create_resp.status_code == 201
    application_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "DRAFT"

    otp_resp = await client.post(f"/api/v1/applications/{application_id}/submit/otp")
    assert otp_resp.status_code == 200
    assert otp_resp.json()["sent"] is True

    submit_resp = await client.post(
        f"/api/v1/applications/{application_id}/submit", json={"code": DEMO_OTP}
    )
    assert submit_resp.status_code == 200
    submitted = submit_resp.json()
    assert submitted["status"] == "IN_PROCESS"
    assert submitted["current_stage_key"] == "SCRUTINY"
    assert submitted["app_no"] and submitted["app_no"].startswith("APP-")

    await _login(client, identifier=officer_phone, role="SCRUTINY_OFFICER")

    queue_resp = await client.get("/api/v1/queue")
    assert queue_resp.status_code == 200
    queue = queue_resp.json()
    assert len(queue) == 1
    assert queue[0]["application_id"] == application_id
    assert "CLEAR" in queue[0]["allowed_actions"]
    stage_id = queue[0]["id"]

    action_resp = await client.post(f"/api/v1/stages/{stage_id}/actions", json={"action": "CLEAR"})
    assert action_resp.status_code == 200
    assert action_resp.json()["status"] == "COMPLETED"

    # SCRUTINY was the last human stage for this pathway -> decision recorded.
    app_resp = await client.get(f"/api/v1/applications/{application_id}")
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "DECISION_RECORDED"

    timeline_resp = await client.get(f"/api/v1/applications/{application_id}/timeline")
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()
    assert len(timeline) > 0
    actions = [entry["action"] for entry in timeline]
    assert any("CLEAR" in a for a in actions)
    assert any(a == "application.submit" for a in actions)


async def test_list_applications_includes_courses(client: AsyncClient) -> None:
    institution_phone, _officer_phone, _institution_id = await _seed_fixtures()
    await _login(client, identifier=institution_phone, role="INSTITUTION")

    await client.post(
        "/api/v1/applications",
        json={
            "application_type": "EXTENSION_OF_APPROVAL",
            "academic_year": "2026-27",
            "payload": {},
            "courses": [
                {"course_name": "CSE", "level": "UG", "existing_intake": 60, "proposed_intake": 90}
            ],
        },
    )

    list_resp = await client.get("/api/v1/applications")
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert len(body) == 1
    assert body[0]["courses"][0]["course_name"] == "CSE"


async def test_institution_cannot_submit_without_valid_otp(client: AsyncClient) -> None:
    institution_phone, _officer_phone, _institution_id = await _seed_fixtures()
    await _login(client, identifier=institution_phone, role="INSTITUTION")

    create_resp = await client.post(
        "/api/v1/applications",
        json={
            "application_type": "EXTENSION_OF_APPROVAL",
            "academic_year": "2026-27",
            "payload": {},
        },
    )
    application_id = create_resp.json()["id"]

    await client.post(f"/api/v1/applications/{application_id}/submit/otp")
    bad_resp = await client.post(
        f"/api/v1/applications/{application_id}/submit", json={"code": "000000"}
    )
    assert bad_resp.status_code == 401
    assert bad_resp.json()["error"]["code"] == "INVALID_OTP"


async def test_officer_cannot_act_on_stage_outside_their_region(client: AsyncClient) -> None:
    institution_phone, officer_phone, _institution_id = await _seed_fixtures()
    await _login(client, identifier=institution_phone, role="INSTITUTION")

    create_resp = await client.post(
        "/api/v1/applications",
        json={
            "application_type": "EXTENSION_OF_APPROVAL",
            "academic_year": "2026-27",
            "payload": {},
        },
    )
    application_id = create_resp.json()["id"]
    await client.post(f"/api/v1/applications/{application_id}/submit/otp")
    await client.post(f"/api/v1/applications/{application_id}/submit", json={"code": DEMO_OTP})

    # a second, unrelated scrutiny officer (different region, never assigned)
    other_officer_phone = f"+9199903{uuid.uuid4().int % 100000:05d}"
    async with SessionLocal() as db:
        other_region = Region(
            code=f"BLR-{uuid.uuid4().hex[:6]}", name="Bangalore", office_city="Bangalore"
        )
        db.add(other_region)
        await db.flush()
        other_officer = User(
            role=UserRole.SCRUTINY_OFFICER,
            name="Other Officer",
            phone_enc=encrypt_field(other_officer_phone),
            phone_hash=hash_identifier(other_officer_phone),
        )
        db.add(other_officer)
        await db.flush()
        db.add(UserRegion(user_id=other_officer.id, region_id=other_region.id))
        await db.commit()

    await _login(client, identifier=officer_phone, role="SCRUTINY_OFFICER")
    queue = (await client.get("/api/v1/queue")).json()
    stage_id = queue[0]["id"]

    await _login(client, identifier=other_officer_phone, role="SCRUTINY_OFFICER")
    resp = await client.post(f"/api/v1/stages/{stage_id}/actions", json={"action": "CLEAR"})
    assert resp.status_code == 404  # out of scope entirely -> not found, not just forbidden
