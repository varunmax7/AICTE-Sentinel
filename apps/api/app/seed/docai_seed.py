"""Phase P3 slice of the seed script (IMPLEMENTATION.md §18.2, Phase P3
task list: "Hero case seed with generated sample PDFs"). Seeds the 5
document types + their extraction schemas, the norms the validators check
against, and the hero case `APP-2026-0451` with 3 generated, genuinely
OCR'd sample documents attached — see `app.services.docai.pipeline`'s
docstring for why extraction runs inline here rather than via Celery.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.db.models.documents import Document, DocumentType, DocumentVersion, Norm
from app.db.models.enums import (
    ApplicationStatus,
    ApplicationType,
    DocumentSource,
    WorkflowRuleStatus,
)
from app.db.models.institution import Institution
from app.db.models.user import User
from app.db.models.workflow import Application, WorkflowRule
from app.seed.sample_pdfs import building_plan_approval_pdf, fire_noc_pdf, lease_deed_pdf
from app.services.docai.pipeline import new_s3_key, run_extraction, sha256_of
from app.services.docai.schemas import (
    AFFIDAVIT,
    BUILDING_PLAN_APPROVAL,
    EXTRACTION_SCHEMAS,
    FACULTY_LIST,
    FIRE_NOC,
    LEASE_DEED,
)
from app.services.storage import ensure_bucket, put_object
from app.services.workflow.engine import route

HERO_APP_NO = "APP-2026-0451"
HERO_ACADEMIC_YEAR = "2026-27"

_DOCUMENT_TYPES: list[tuple[str, str, bool, int | None]] = [
    (LEASE_DEED, "documentType.leaseDeed", True, 10),
    (BUILDING_PLAN_APPROVAL, "documentType.buildingPlanApproval", False, None),
    (FIRE_NOC, "documentType.fireNoc", True, 1),
    (AFFIDAVIT, "documentType.affidavit", False, None),
    (FACULTY_LIST, "documentType.facultyList", False, None),
]

_NORMS: list[tuple[str, str, float, str]] = [
    ("LAND_AREA_MIN_ACRES", ApplicationType.NEW_INSTITUTION.value, 5.0, "acres"),
    ("STAMP_DUTY_RATE_PER_ACRE", ApplicationType.NEW_INSTITUTION.value, 50000.0, "INR/acre"),
    ("LAND_AREA_MIN_ACRES", ApplicationType.CHANGE_OF_SITE.value, 5.0, "acres"),
    ("STAMP_DUTY_RATE_PER_ACRE", ApplicationType.CHANGE_OF_SITE.value, 50000.0, "INR/acre"),
]


async def _seed_document_types(db: AsyncSession) -> None:
    for code, name_key, has_expiry, min_validity_years in _DOCUMENT_TYPES:
        existing = await db.execute(select(DocumentType).where(DocumentType.code == code))
        if existing.scalar_one_or_none() is None:
            db.add(
                DocumentType(
                    code=code,
                    name_key=name_key,
                    has_expiry=has_expiry,
                    extraction_schema=EXTRACTION_SCHEMAS.get(code, []),
                    min_validity_years=min_validity_years,
                )
            )


async def _seed_norms(db: AsyncSession) -> None:
    for key, application_type, value, unit in _NORMS:
        existing = await db.execute(
            select(Norm).where(Norm.key == key, Norm.application_type == application_type)
        )
        if existing.scalar_one_or_none() is None:
            db.add(Norm(key=key, application_type=application_type, value=value, unit=unit))


async def _upload_and_extract(
    db: AsyncSession,
    *,
    institution: Institution,
    application: Application,
    user: User,
    document_type: str,
    pdf_bytes: bytes,
) -> None:
    key = new_s3_key(
        institution_id=institution.id,
        document_type=document_type,
        filename=f"{document_type.lower()}.pdf",
    )
    put_object(key, pdf_bytes, content_type="application/pdf")

    document = Document(
        institution_id=institution.id, application_id=application.id, document_type=document_type
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
        at=clock.now(),
    )
    db.add(version)
    await db.flush()
    document.current_version_id = version.id
    await db.commit()

    await run_extraction(db, version)


async def seed_hero_case(
    db: AsyncSession, *, institution: Institution, institution_user: User
) -> None:
    ensure_bucket()
    await _seed_document_types(db)
    await _seed_norms(db)
    await db.commit()

    existing = await db.execute(select(Application).where(Application.app_no == HERO_APP_NO))
    if existing.scalar_one_or_none() is not None:
        return  # already seeded on a previous run

    rule_result = await db.execute(
        select(WorkflowRule).where(
            WorkflowRule.application_type == ApplicationType.NEW_INSTITUTION,
            WorkflowRule.academic_year == HERO_ACADEMIC_YEAR,
            WorkflowRule.status == WorkflowRuleStatus.PUBLISHED,
        )
    )
    rule = rule_result.scalar_one_or_none()
    if rule is None:
        return  # Phase P2's workflow seed hasn't run yet — nothing to attach the hero case to

    hero = Application(
        institution_id=institution.id,
        application_type=ApplicationType.NEW_INSTITUTION,
        academic_year=HERO_ACADEMIC_YEAR,
        rule_id=rule.id,
        app_no=HERO_APP_NO,
        status=ApplicationStatus.SUBMITTED,
        payload={"is_government": True},
        submitted_at=clock.now(),
    )
    db.add(hero)
    await db.commit()

    await route(db, hero)

    await _upload_and_extract(
        db,
        institution=institution,
        application=hero,
        user=institution_user,
        document_type=LEASE_DEED,
        pdf_bytes=lease_deed_pdf(
            lessor="Telangana State Industrial Infrastructure Corporation",
            lessee=institution.name,
            survey_no="145/2A",
            land_area_acres=5.2,
            start_date="01-Apr-2020",
            expiry_date="31-Mar-2040",
            registration_no="TS-REG-2020-00451",
            stamp_duty_amount=45000,
        ),
    )
    await _upload_and_extract(
        db,
        institution=institution,
        application=hero,
        user=institution_user,
        document_type=FIRE_NOC,
        pdf_bytes=fire_noc_pdf(
            issuing_authority="Telangana State Fire Services",
            issued_date="15-Jan-2026",
            expiry_date="14-Jan-2027",
        ),
    )
    await _upload_and_extract(
        db,
        institution=institution,
        application=hero,
        user=institution_user,
        document_type=BUILDING_PLAN_APPROVAL,
        pdf_bytes=building_plan_approval_pdf(
            approval_no="GHMC-BP-2026-00451", approved_date="10-Feb-2026", built_up_area_sqft=42000
        ),
    )

    print(f"Hero case {HERO_APP_NO} seeded with 3 extracted documents.")
