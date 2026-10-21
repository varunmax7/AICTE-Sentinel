"""Document upload/retrieval/verification endpoints (IMPLEMENTATION.md
§13.4) plus the application pre-scrutiny report. Downloads/previews stream
through this app rather than handing out bare S3 presigned URLs — see
`app.services.storage`'s docstring for why.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import now
from app.core.deps import get_current_user, require
from app.db.models.documents import AiCheck, Document, DocumentType, DocumentVersion, Extraction
from app.db.models.enums import AiCheckStatus, DocumentSource, UserRole
from app.db.models.user import User
from app.db.models.workflow import Application
from app.db.session import get_db
from app.routers.stages import OFFICER_ROLES
from app.schemas.documents import (
    AiCheckOut,
    AiReportOut,
    DocumentOut,
    DocumentTypeOut,
    DocumentVerifyRequest,
    DocumentVersionOut,
    ExtractionOut,
)
from app.services.docai.pipeline import (
    new_s3_key,
    run_application_checks,
    run_extraction,
    sha256_of,
)
from app.services.storage import get_object, put_object
from app.services.workflow.scope import institution_in_scope

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])


@router.get("/document-types", response_model=list[DocumentTypeOut])
async def list_document_types(
    _user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[DocumentTypeOut]:
    result = await db.execute(select(DocumentType).order_by(DocumentType.code))
    return [
        DocumentTypeOut(
            code=t.code,
            name_key=t.name_key,
            has_expiry=t.has_expiry,
            extraction_schema=t.extraction_schema,
            min_validity_years=t.min_validity_years,
        )
        for t in result.scalars()
    ]


async def _to_document_out(db: AsyncSession, document: Document) -> DocumentOut:
    versions_result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version.desc())
    )
    versions = list(versions_result.scalars())

    extraction_out = None
    if document.current_version_id is not None:
        extraction_result = await db.execute(
            select(Extraction)
            .where(Extraction.document_version_id == document.current_version_id)
            .order_by(Extraction.at.desc())
            .limit(1)
        )
        extraction = extraction_result.scalar_one_or_none()
        if extraction is not None:
            extraction_out = ExtractionOut(
                id=str(extraction.id),
                model_id=extraction.model_id,
                fields=extraction.fields,
                boxes=extraction.boxes,
                confidence=float(extraction.confidence),
                page_count=extraction.page_count,
                status=extraction.status,
            )

    current_version = next((v for v in versions if v.id == document.current_version_id), None)

    return DocumentOut(
        id=str(document.id),
        institution_id=str(document.institution_id),
        application_id=str(document.application_id) if document.application_id else None,
        document_type=document.document_type,
        current_version_id=str(document.current_version_id)
        if document.current_version_id
        else None,
        expiry_date=document.expiry_date,
        verified_status=document.verified_status,
        verified_by=str(document.verified_by) if document.verified_by else None,
        verified_at=document.verified_at,
        versions=[
            DocumentVersionOut(
                id=str(v.id),
                version=v.version,
                mime=v.mime,
                size=v.size,
                sha256=v.sha256,
                source=v.source.value,
                at=v.at,
            )
            for v in versions
        ],
        extraction=extraction_out,
        preview_url=f"/api/v1/documents/{document.id}/preview"
        if current_version and current_version.preview_s3_key
        else None,
        download_url=f"/api/v1/documents/{document.id}/download",
    )


async def _get_scoped_document(db: AsyncSession, user: User, document_id: uuid.UUID) -> Document:
    document = await db.get(Document, document_id)
    if document is None or not await institution_in_scope(db, user, document.institution_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "DOCUMENT_NOT_FOUND"})
    return document


@router.post("/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    application_id: uuid.UUID = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(require(UserRole.INSTITUTION)),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    application = await db.get(Application, application_id)
    if application is None or application.institution_id != user.institution_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "APPLICATION_NOT_FOUND"})

    type_result = await db.execute(select(DocumentType).where(DocumentType.code == document_type))
    type_row = type_result.scalar_one_or_none()
    if type_row is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "DOCUMENT_TYPE_NOT_FOUND"})

    data = await file.read()
    assert user.institution_id is not None  # guaranteed by require(UserRole.INSTITUTION)
    key = new_s3_key(
        institution_id=user.institution_id,
        document_type=document_type,
        filename=file.filename or "upload.pdf",
    )
    put_object(key, data, content_type=file.content_type or "application/pdf")

    document = Document(
        institution_id=user.institution_id,
        application_id=application.id,
        document_type=document_type,
    )
    db.add(document)
    await db.flush()

    version = DocumentVersion(
        document_id=document.id,
        version=1,
        s3_key=key,
        sha256=sha256_of(data),
        mime=file.content_type or "application/pdf",
        size=len(data),
        uploaded_by=user.id,
        source=DocumentSource.PORTAL,
        at=now(),
    )
    db.add(version)
    await db.flush()
    document.current_version_id = version.id
    await db.commit()

    try:
        await run_extraction(db, version)
    except Exception:  # noqa: BLE001 - extraction failure must not fail the upload itself
        logger.exception("Extraction failed for document_version=%s", version.id)

    await db.refresh(document)
    return await _to_document_out(db, document)


@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    document = await _get_scoped_document(db, user, document_id)
    return await _to_document_out(db, document)


@router.get("/documents/{document_id}/extraction", response_model=ExtractionOut)
async def get_document_extraction(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractionOut:
    document = await _get_scoped_document(db, user, document_id)
    out = await _to_document_out(db, document)
    if out.extraction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "EXTRACTION_NOT_FOUND"})
    return out.extraction


@router.get("/documents/{document_id}/preview")
async def get_document_preview(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    document = await _get_scoped_document(db, user, document_id)
    if document.current_version_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "PREVIEW_NOT_FOUND"})
    version = await db.get(DocumentVersion, document.current_version_id)
    if version is None or not version.preview_s3_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "PREVIEW_NOT_FOUND"})
    data = get_object(version.preview_s3_key)
    return StreamingResponse(iter([data]), media_type="image/png")


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    document = await _get_scoped_document(db, user, document_id)
    if document.current_version_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "DOCUMENT_HAS_NO_VERSION"})
    version = await db.get(DocumentVersion, document.current_version_id)
    assert version is not None
    data = get_object(version.s3_key)
    return StreamingResponse(iter([data]), media_type=version.mime)


@router.post("/documents/{document_id}/verify", response_model=DocumentOut)
async def verify_document(
    document_id: uuid.UUID,
    body: DocumentVerifyRequest,
    user: User = Depends(require(*OFFICER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    document = await _get_scoped_document(db, user, document_id)

    if body.fields is not None and document.current_version_id is not None:
        extraction_result = await db.execute(
            select(Extraction)
            .where(Extraction.document_version_id == document.current_version_id)
            .order_by(Extraction.at.desc())
            .limit(1)
        )
        extraction = extraction_result.scalar_one_or_none()
        if extraction is not None:
            merged: dict[str, Any] = dict(extraction.fields)
            for field_name, value in body.fields.items():
                existing = dict(merged.get(field_name, {}))
                existing["value"] = value
                existing["human_verified"] = True
                merged[field_name] = existing
            extraction.fields = merged

    document.verified_status = body.result
    document.verified_by = user.id
    document.verified_at = now()
    if body.expiry_date is not None:
        document.expiry_date = body.expiry_date

    await db.commit()

    if document.application_id is not None:
        application = await db.get(Application, document.application_id)
        if application is not None:
            await run_application_checks(db, application)
            await db.commit()

    await db.refresh(document)
    return await _to_document_out(db, document)


@router.get("/applications/{application_id}/documents", response_model=list[DocumentOut])
async def list_application_documents(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    application = await db.get(Application, application_id)
    if application is None or not await institution_in_scope(db, user, application.institution_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "APPLICATION_NOT_FOUND"})
    result = await db.execute(select(Document).where(Document.application_id == application_id))
    return [await _to_document_out(db, d) for d in result.scalars()]


@router.get("/applications/{application_id}/ai-report", response_model=AiReportOut)
async def get_application_ai_report(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AiReportOut:
    application = await db.get(Application, application_id)
    if application is None or not await institution_in_scope(db, user, application.institution_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "APPLICATION_NOT_FOUND"})

    checks_result = await db.execute(
        select(AiCheck).where(AiCheck.application_id == application_id)
    )
    checks = list(checks_result.scalars())

    pass_weight = {AiCheckStatus.PASS: 100.0, AiCheckStatus.WARN: 60.0, AiCheckStatus.FAIL: 0.0}
    confidence = (
        round(sum(pass_weight[c.status] for c in checks) / len(checks), 2) if checks else 0.0
    )

    return AiReportOut(
        application_id=str(application_id),
        confidence=confidence,
        checks=[
            AiCheckOut(
                check_key=c.check_key, status=c.status, message_key=c.message_key, params=c.params
            )
            for c in checks
        ],
    )
