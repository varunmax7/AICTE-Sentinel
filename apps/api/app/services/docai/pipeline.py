"""Orchestrates one document version through extraction + validation, and
an application through its pre-scrutiny checks (IMPLEMENTATION.md §14).

Called two ways, both against the same functions here so there is exactly
one implementation to keep correct: directly (awaited inline) from the
upload endpoint, so a demo upload shows real results in the same request
without needing a running Celery worker; and from the `ocr_extract` Celery
task (`app.workers.tasks.docai`) for contexts with no HTTP request to
answer — a future inbound-email/WhatsApp attachment (Phase P7), or an
admin "re-run extraction" action.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import now
from app.db.models.documents import (
    AiCheck,
    Document,
    DocumentType,
    DocumentVersion,
    Extraction,
    Norm,
)
from app.db.models.enums import ActorType, ExtractionStatus
from app.db.models.workflow import Application, ApplicationTypeDef
from app.services.audit.chain import write_audit_event
from app.services.docai.extract import extract_document
from app.services.docai.validators import (
    check_document_validity,
    check_duplicate_faculty,
    check_land_area_norms,
    check_required_documents_present,
    check_stamp_duty_sanity,
)
from app.services.events import emit_event
from app.services.storage import get_object, put_object

STAMP_DUTY_RATE_PER_ACRE_DEFAULT = 50_000.0


async def run_extraction(db: AsyncSession, document_version: DocumentVersion) -> Extraction:
    document = await db.get(Document, document_version.document_id)
    assert document is not None

    pdf_bytes = get_object(document_version.s3_key)
    result = extract_document(pdf_bytes, document_type=document.document_type)

    if result.preview_png:
        preview_key = f"{document_version.s3_key}.preview.png"
        put_object(preview_key, result.preview_png, content_type="image/png")
        document_version.preview_s3_key = preview_key

    extraction = Extraction(
        document_version_id=document_version.id,
        model_id="regex-ocr-v1",
        fields=result.fields,
        boxes=result.boxes,
        raw_text=result.raw_text,
        confidence=result.confidence,
        page_count=result.page_count,
        status=ExtractionStatus.DONE if result.fields else ExtractionStatus.FAILED,
        at=now(),
    )
    db.add(extraction)
    await db.flush()

    if document.application_id is not None:
        application = await db.get(Application, document.application_id)
        if application is not None:
            await run_application_checks(db, application)

    await db.commit()
    return extraction


async def _latest_extraction(db: AsyncSession, document: Document) -> Extraction | None:
    if document.current_version_id is None:
        return None
    result = await db.execute(
        select(Extraction)
        .where(Extraction.document_version_id == document.current_version_id)
        .order_by(Extraction.at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _norm_value(db: AsyncSession, *, key: str, application_type: str) -> float | None:
    result = await db.execute(
        select(Norm.value).where(Norm.key == key, Norm.application_type == application_type)
    )
    value = result.scalar_one_or_none()
    return float(value) if value is not None else None


def _field(extraction: Extraction | None, name: str) -> str | None:
    if extraction is None:
        return None
    entry = extraction.fields.get(name)
    return entry.get("value") if entry else None


async def run_application_checks(db: AsyncSession, application: Application) -> list[AiCheck]:
    """(Re)computes every `ai_checks` row for an application — replaces any
    existing rows so re-running (e.g. after a corrected re-upload) doesn't
    accumulate stale checks.
    """

    existing = await db.execute(select(AiCheck).where(AiCheck.application_id == application.id))
    for row in existing.scalars():
        await db.delete(row)
    await db.flush()

    documents_result = await db.execute(
        select(Document).where(Document.application_id == application.id)
    )
    documents = list(documents_result.scalars())
    uploaded_codes = {d.document_type for d in documents}

    lease = next((d for d in documents if d.document_type == "LEASE_DEED"), None)
    lease_extraction = await _latest_extraction(db, lease) if lease else None

    land_area_str = _field(lease_extraction, "land_area_acres")
    stamp_duty_str = _field(lease_extraction, "stamp_duty_amount")
    expiry_str = _field(lease_extraction, "expiry_date")

    land_area = float(land_area_str) if land_area_str else None
    stamp_duty = float(stamp_duty_str.replace(",", "")) if stamp_duty_str else None

    required_acres = await _norm_value(
        db, key="LAND_AREA_MIN_ACRES", application_type=application.application_type.value
    )
    rate_per_acre = (
        await _norm_value(
            db, key="STAMP_DUTY_RATE_PER_ACRE", application_type=application.application_type.value
        )
        or STAMP_DUTY_RATE_PER_ACRE_DEFAULT
    )

    checks = [
        check_land_area_norms(extracted_acres=land_area, required_acres=required_acres),
        check_stamp_duty_sanity(
            stamp_duty_amount=stamp_duty, land_area_acres=land_area, rate_per_acre=rate_per_acre
        ),
        check_duplicate_faculty(),
    ]

    if lease is not None:
        lease_type_result = await db.execute(
            select(DocumentType).where(DocumentType.code == "LEASE_DEED")
        )
        lease_type = lease_type_result.scalar_one_or_none()
        checks.append(
            check_document_validity(
                expiry_date_str=expiry_str,
                min_validity_years=lease_type.min_validity_years if lease_type else None,
                reference=date.today(),
            )
        )

    type_result = await db.execute(
        select(ApplicationTypeDef).where(ApplicationTypeDef.code == application.application_type)
    )
    type_row = type_result.scalar_one_or_none()
    required_codes = type_row.required_document_types if type_row else []

    checks.append(
        check_required_documents_present(
            required_codes=required_codes, uploaded_codes=uploaded_codes
        )
    )

    rows: list[AiCheck] = []
    for check in checks:
        row = AiCheck(
            application_id=application.id,
            check_key=check["check_key"],
            status=check["status"],
            message_key=check["message_key"],
            params=check["params"],
            at=now(),
        )
        db.add(row)
        rows.append(row)
    await db.flush()

    await write_audit_event(
        db,
        actor_type=ActorType.AI,
        actor_id=None,
        action="application.ai_checks_computed",
        entity_type="application",
        entity_id=application.id,
        application_id=application.id,
        after={"checks": [c["check_key"] for c in checks]},
    )
    await emit_event(
        db,
        "application.ai_checks_updated",
        {"application_id": str(application.id), "checks": [c["check_key"] for c in checks]},
    )
    return rows


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def new_s3_key(*, institution_id: uuid.UUID, document_type: str, filename: str) -> str:
    return f"institutions/{institution_id}/{document_type}/{uuid.uuid4().hex}-{filename}"
