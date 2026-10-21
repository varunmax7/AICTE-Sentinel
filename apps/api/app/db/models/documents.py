"""Document AI tables (IMPLEMENTATION.md §14, §21): document types, the
uploaded documents + their versions, OCR/LLM extractions, validator-produced
checks, and anomaly flags. See `app.services.docai` for the pipeline that
populates `extractions`/`ai_checks`/`ai_flags`.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import ARRAY, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin
from app.db.models.enums import (
    AiCheckStatus,
    AiFlagSeverity,
    AiFlagStatus,
    DocumentSource,
    DocumentVerifiedStatus,
    ExtractionStatus,
)


class DocumentType(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "document_types"

    code: Mapped[str] = mapped_column(String(64), unique=True)
    name_key: Mapped[str] = mapped_column(String(128))
    has_expiry: Mapped[bool] = mapped_column(Boolean, default=False)
    extraction_schema: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    min_validity_years: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Document(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "documents"

    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id"))
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("applications.id"), nullable=True
    )
    # No `compliance_items` table until Phase P6 — plain UUID, no FK yet (§21).
    compliance_item_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    document_type: Mapped[str] = mapped_column(ForeignKey("document_types.code"))
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_versions.id", use_alter=True, name="fk_documents_current_version_id"),
        nullable=True,
    )
    expiry_date: Mapped[date | None] = mapped_column(nullable=True)
    verified_status: Mapped[DocumentVerifiedStatus] = mapped_column(
        Enum(DocumentVerifiedStatus, name="document_verified_status"),
        default=DocumentVerifiedStatus.UNVERIFIED,
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentVersion(Base, UUIDPKMixin):
    __tablename__ = "document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"))
    version: Mapped[int] = mapped_column(Integer)
    s3_key: Mapped[str] = mapped_column(String(512))
    preview_s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64))
    mime: Mapped[str] = mapped_column(String(128))
    size: Mapped[int] = mapped_column(Integer)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    source: Mapped[DocumentSource] = mapped_column(
        Enum(DocumentSource, name="document_source"), default=DocumentSource.PORTAL
    )
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Extraction(Base, UUIDPKMixin):
    __tablename__ = "extractions"

    document_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_versions.id"))
    model_id: Mapped[str] = mapped_column(String(128))
    fields: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    boxes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus, name="extraction_status"), default=ExtractionStatus.PENDING
    )
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AiCheck(Base, UUIDPKMixin):
    __tablename__ = "ai_checks"

    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"))
    check_key: Mapped[str] = mapped_column(String(64))
    status: Mapped[AiCheckStatus] = mapped_column(Enum(AiCheckStatus, name="ai_check_status"))
    message_key: Mapped[str] = mapped_column(String(128))
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AiFlag(Base, UUIDPKMixin):
    __tablename__ = "ai_flags"

    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True))
    flag_key: Mapped[str] = mapped_column(String(64))
    severity: Mapped[AiFlagSeverity] = mapped_column(Enum(AiFlagSeverity, name="ai_flag_severity"))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[AiFlagStatus] = mapped_column(
        Enum(AiFlagStatus, name="ai_flag_status"), default=AiFlagStatus.OPEN
    )
    dismissed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Norm(Base, UUIDPKMixin):
    __tablename__ = "norms"

    key: Mapped[str] = mapped_column(String(64))
    application_type: Mapped[str] = mapped_column(String(32))
    value: Mapped[float] = mapped_column(Numeric(10, 2))
    unit: Mapped[str] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
