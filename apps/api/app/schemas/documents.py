from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.db.models.enums import AiCheckStatus, DocumentVerifiedStatus, ExtractionStatus


class DocumentTypeOut(BaseModel):
    code: str
    name_key: str
    has_expiry: bool
    extraction_schema: list[str]
    min_validity_years: int | None


class DocumentVersionOut(BaseModel):
    id: str
    version: int
    mime: str
    size: int
    sha256: str
    source: str
    at: datetime


class ExtractionOut(BaseModel):
    id: str
    model_id: str
    fields: dict[str, Any]
    boxes: list[dict[str, Any]]
    confidence: float
    page_count: int
    status: ExtractionStatus


class DocumentOut(BaseModel):
    id: str
    institution_id: str
    application_id: str | None
    document_type: str
    current_version_id: str | None
    expiry_date: date | None
    verified_status: DocumentVerifiedStatus
    verified_by: str | None
    verified_at: datetime | None
    versions: list[DocumentVersionOut]
    extraction: ExtractionOut | None
    preview_url: str | None
    download_url: str


class DocumentVerifyRequest(BaseModel):
    fields: dict[str, Any] | None = None
    expiry_date: date | None = None
    result: DocumentVerifiedStatus = DocumentVerifiedStatus.VERIFIED


class AiCheckOut(BaseModel):
    check_key: str
    status: AiCheckStatus
    message_key: str
    params: dict[str, Any]


class AiReportOut(BaseModel):
    application_id: str
    confidence: float
    checks: list[AiCheckOut]
