"""HTTP-level test of the Phase P3 documents API: an institution uploads a
real generated lease deed PDF to their application, the upload response
already carries real OCR-extracted fields and a check-worthy confidence,
an officer can download/preview it and verify it, and the application's
AI pre-scrutiny report reflects the resulting checks.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from app.core.security import encrypt_field, hash_identifier
from app.db.models.documents import DocumentType
from app.db.models.documents import Norm as NormModel
from app.db.models.enums import ApplicationType, InstitutionType, UserRole, WorkflowRuleStatus
from app.db.models.geo import Region, State
from app.db.models.institution import Institution
from app.db.models.user import User, UserRegion
from app.db.models.workflow import Application, ApplicationTypeDef, WorkflowRule
from app.db.session import SessionLocal
from app.seed.sample_pdfs import lease_deed_pdf
from app.services.docai.schemas import EXTRACTION_SCHEMAS, LEASE_DEED

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
    institution_phone = f"+9199905{uuid.uuid4().int % 100000:05d}"
    officer_phone = f"+9199906{uuid.uuid4().int % 100000:05d}"

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
            name="API Doc Test College",
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
            rule_key=f"NEW_INSTITUTION@test@{uuid.uuid4().hex[:8]}",
            application_type=ApplicationType.NEW_INSTITUTION,
            academic_year="2026-27",
            version=1,
            definition={
                "rule_id": "test",
                "application_type": "NEW_INSTITUTION",
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
                code=ApplicationType.NEW_INSTITUTION,
                name_key="x",
                required_document_types=[LEASE_DEED],
                default_rule_id=rule.id,
            )
        )
        db.add(
            DocumentType(
                code=LEASE_DEED,
                name_key="x",
                has_expiry=True,
                extraction_schema=EXTRACTION_SCHEMAS[LEASE_DEED],
                min_validity_years=10,
            )
        )
        db.add(
            NormModel(
                key="LAND_AREA_MIN_ACRES",
                application_type="NEW_INSTITUTION",
                value=5.0,
                unit="acres",
            )
        )
        db.add(
            NormModel(
                key="STAMP_DUTY_RATE_PER_ACRE",
                application_type="NEW_INSTITUTION",
                value=50000.0,
                unit="INR/acre",
            )
        )

        application = Application(
            institution_id=institution.id,
            application_type=ApplicationType.NEW_INSTITUTION,
            academic_year="2026-27",
            rule_id=rule.id,
            app_no="APP-2026-9001",
            payload={},
        )
        db.add(application)
        await db.commit()
        application_id = str(application.id)

    return institution_phone, officer_phone, application_id


async def _login(client: AsyncClient, *, identifier: str, role: str) -> None:
    await client.post("/api/v1/auth/otp/send", json={"identifier": identifier, "role": role})
    resp = await client.post(
        "/api/v1/auth/otp/verify", json={"identifier": identifier, "role": role, "code": DEMO_OTP}
    )
    assert resp.status_code == 200


async def test_upload_extracts_real_fields_and_feeds_ai_report(client: AsyncClient) -> None:
    institution_phone, officer_phone, application_id = await _seed_fixtures()
    await _login(client, identifier=institution_phone, role="INSTITUTION")

    pdf_bytes = lease_deed_pdf(
        lessor="Telangana SIIC",
        lessee="API Doc Test College",
        survey_no="145/2A",
        land_area_acres=5.2,
        start_date="01-Apr-2020",
        expiry_date="31-Mar-2040",
        registration_no="TS-REG-2020-00451",
        stamp_duty_amount=45000,
    )

    upload_resp = await client.post(
        "/api/v1/documents",
        data={"application_id": application_id, "document_type": LEASE_DEED},
        files={"file": ("lease.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_resp.status_code == 201
    body = upload_resp.json()
    assert body["extraction"] is not None
    assert body["extraction"]["fields"]["land_area_acres"]["value"] == "5.2"
    assert body["download_url"].endswith("/download")
    document_id = body["id"]

    get_resp = await client.get(f"/api/v1/documents/{document_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["extraction"]["fields"]["stamp_duty_amount"]["value"] == "45000"

    download_resp = await client.get(f"/api/v1/documents/{document_id}/download")
    assert download_resp.status_code == 200
    assert download_resp.content[:4] == b"%PDF"

    preview_resp = await client.get(f"/api/v1/documents/{document_id}/preview")
    assert preview_resp.status_code == 200
    assert preview_resp.content[:8] == b"\x89PNG\r\n\x1a\n"

    report_resp = await client.get(f"/api/v1/applications/{application_id}/ai-report")
    assert report_resp.status_code == 200
    report = report_resp.json()
    checks_by_key = {c["check_key"]: c for c in report["checks"]}
    assert checks_by_key["LAND_AREA_NORMS"]["status"] == "PASS"
    assert checks_by_key["STAMP_DUTY_SANITY"]["status"] == "WARN"
    assert report["confidence"] > 0

    await _login(client, identifier=officer_phone, role="SCRUTINY_OFFICER")
    verify_resp = await client.post(
        f"/api/v1/documents/{document_id}/verify",
        json={"result": "VERIFIED", "fields": {"land_area_acres": "5.2"}},
    )
    assert verify_resp.status_code == 200
    verified = verify_resp.json()
    assert verified["verified_status"] == "VERIFIED"
    assert verified["verified_by"] is not None


async def test_upload_rejects_unknown_document_type(client: AsyncClient) -> None:
    institution_phone, _officer_phone, application_id = await _seed_fixtures()
    await _login(client, identifier=institution_phone, role="INSTITUTION")

    resp = await client.post(
        "/api/v1/documents",
        data={"application_id": application_id, "document_type": "NOT_A_REAL_TYPE"},
        files={"file": ("x.pdf", b"%PDF-1.4 not a real pdf", "application/pdf")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DOCUMENT_TYPE_NOT_FOUND"
