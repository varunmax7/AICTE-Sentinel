"""Document AI pipeline tests (IMPLEMENTATION.md §19 Phase P3 acceptance):
real OCR extraction of a generated lease deed finds the land area, the
land-area-norms and stamp-duty-sanity validators produce the right
PASS/WARN verdicts from it, and `run_application_checks` recomputes
cleanly on re-run.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.clock import now
from app.core.security import encrypt_field, hash_identifier
from app.db.models.documents import AiCheck, Document, DocumentType, DocumentVersion, Norm
from app.db.models.enums import (
    ApplicationStatus,
    ApplicationType,
    DocumentSource,
    InstitutionType,
    UserRole,
)
from app.db.models.geo import Region, State
from app.db.models.institution import Institution
from app.db.models.user import User
from app.db.models.workflow import Application
from app.db.session import SessionLocal
from app.seed.sample_pdfs import lease_deed_pdf
from app.services.docai.extract import extract_document
from app.services.docai.pipeline import (
    new_s3_key,
    run_application_checks,
    run_extraction,
    sha256_of,
)
from app.services.docai.schemas import EXTRACTION_SCHEMAS, LEASE_DEED
from app.services.storage import ensure_bucket, put_object


def test_extract_document_finds_land_area_and_stamp_duty() -> None:
    pdf_bytes = lease_deed_pdf(
        lessor="Test Lessor",
        lessee="Test College",
        survey_no="99/1",
        land_area_acres=5.2,
        start_date="01-Apr-2020",
        expiry_date="31-Mar-2040",
        registration_no="REG-1",
        stamp_duty_amount=45000,
    )
    result = extract_document(pdf_bytes, document_type=LEASE_DEED)
    assert result.fields["land_area_acres"]["value"] == "5.2"
    assert result.fields["stamp_duty_amount"]["value"] == "45000"
    assert result.confidence > 0
    assert len(result.boxes) > 0


async def _make_institution_and_application() -> tuple[Institution, Application]:
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
            name="Test College",
            type=InstitutionType.GOVT,
            state_id=state.id,
            region_id=region.id,
            city="Hyderabad",
            address="Addr",
        )
        db.add(institution)
        await db.flush()
        application = Application(
            institution_id=institution.id,
            application_type=ApplicationType.NEW_INSTITUTION,
            academic_year="2026-27",
            status=ApplicationStatus.IN_PROCESS,
            payload={},
        )
        db.add(application)

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
            Norm(
                key="LAND_AREA_MIN_ACRES",
                application_type="NEW_INSTITUTION",
                value=5.0,
                unit="acres",
            )
        )
        db.add(
            Norm(
                key="STAMP_DUTY_RATE_PER_ACRE",
                application_type="NEW_INSTITUTION",
                value=50000.0,
                unit="INR/acre",
            )
        )
        await db.commit()
        return institution, application


async def _upload_lease_deed(
    institution: Institution, application: Application, *, stamp_duty: int
) -> None:
    ensure_bucket()
    phone = f"+9199904{uuid.uuid4().int % 100000:05d}"
    async with SessionLocal() as db:
        user = User(
            role=UserRole.INSTITUTION,
            name="Uploader",
            phone_enc=encrypt_field(phone),
            phone_hash=hash_identifier(phone),
            institution_id=institution.id,
        )
        db.add(user)
        await db.flush()

        pdf_bytes = lease_deed_pdf(
            lessor="Test Lessor",
            lessee=institution.name,
            survey_no="99/1",
            land_area_acres=5.2,
            start_date="01-Apr-2020",
            expiry_date="31-Mar-2040",
            registration_no="REG-1",
            stamp_duty_amount=stamp_duty,
        )
        key = new_s3_key(
            institution_id=institution.id, document_type=LEASE_DEED, filename="lease.pdf"
        )
        put_object(key, pdf_bytes, content_type="application/pdf")

        document = Document(
            institution_id=institution.id, application_id=application.id, document_type=LEASE_DEED
        )
        db.add(document)
        await db.flush()

        version = DocumentVersion(
            document_id=document.id,
            version=1,
            s3_key=key,
            sha256=sha256_of(pdf_bytes),
            mime="application/pdf",
            size=len(pdf_bytes),
            uploaded_by=user.id,
            source=DocumentSource.PORTAL,
            at=now(),
        )
        db.add(version)
        await db.flush()
        document.current_version_id = version.id
        await db.commit()

        await run_extraction(db, version)


async def test_run_application_checks_passes_land_area_and_warns_stamp_duty() -> None:
    institution, application = await _make_institution_and_application()
    await _upload_lease_deed(institution, application, stamp_duty=45000)

    async with SessionLocal() as db:
        checks = await run_application_checks(db, await db.get(Application, application.id))
        await db.commit()

        by_key = {c.check_key: c for c in checks}
        assert by_key["LAND_AREA_NORMS"].status.value == "PASS"
        assert by_key["LAND_AREA_NORMS"].params["extracted"] == 5.2
        assert by_key["STAMP_DUTY_SANITY"].status.value == "WARN"


async def test_run_application_checks_passes_stamp_duty_when_adequate() -> None:
    institution, application = await _make_institution_and_application()
    # 5.2 acres * 50000/acre = 260000 expected; well above the *0.5 warn threshold.
    await _upload_lease_deed(institution, application, stamp_duty=300000)

    async with SessionLocal() as db:
        checks = await run_application_checks(db, await db.get(Application, application.id))
        by_key = {c.check_key: c for c in checks}
        assert by_key["STAMP_DUTY_SANITY"].status.value == "PASS"


async def test_run_application_checks_is_idempotent_on_rerun() -> None:
    institution, application = await _make_institution_and_application()
    await _upload_lease_deed(institution, application, stamp_duty=45000)

    async with SessionLocal() as db:
        await run_application_checks(db, await db.get(Application, application.id))
        await db.commit()

    async with SessionLocal() as db:
        await run_application_checks(db, await db.get(Application, application.id))
        await db.commit()

    async with SessionLocal() as db:
        result = await db.execute(select(AiCheck).where(AiCheck.application_id == application.id))
        rows = list(result.scalars())
        # exactly one row per check_key, not accumulated across the two runs.
        assert len({r.check_key for r in rows}) == len(rows)
