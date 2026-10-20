"""Workflow engine tables (IMPLEMENTATION.md §9, §21): application types,
versioned JSON rules, applications, and the per-application stage machine
(stage instances, transitions, assignments, deficiencies, deficiency
letters). See `app.services.workflow` for the engine that operates on these.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin
from app.db.models.enums import (
    ApplicationStatus,
    ApplicationType,
    DeficiencyStatus,
    StageStatus,
    WorkflowRuleStatus,
)


class ApplicationTypeDef(Base, UUIDPKMixin, TimestampMixin):
    """Master row per application type — `code` mirrors the `ApplicationType`
    enum. A separate table (rather than just the enum) because §21 wants
    `required_document_types` and `default_rule_id` attached, and P10's admin
    screen manages this as data, not code.
    """

    __tablename__ = "application_types"

    code: Mapped[ApplicationType] = mapped_column(
        Enum(ApplicationType, name="application_type_code"), unique=True
    )
    name_key: Mapped[str] = mapped_column(String(128))
    required_document_types: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    default_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_rules.id"), nullable=True
    )


class WorkflowRule(Base, UUIDPKMixin, TimestampMixin):
    """Versioned rule definition (§9.2). `definition` is the validated JSON
    document (see `app.services.workflow.rules.RuleDefinition`) — stages,
    SLAs, actions, branches. Never mutated in place: a rule edit in the admin
    UI (P10) creates a new version instead, so in-flight applications keep
    referencing the exact rule they were routed under.
    """

    __tablename__ = "workflow_rules"
    __table_args__ = (
        UniqueConstraint("application_type", "academic_year", "version", name="uq_rule_version"),
    )

    rule_key: Mapped[str] = mapped_column(String(128), unique=True)
    application_type: Mapped[ApplicationType] = mapped_column(
        Enum(ApplicationType, name="application_type_code")
    )
    academic_year: Mapped[str] = mapped_column(String(16))
    version: Mapped[int] = mapped_column(Integer)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[WorkflowRuleStatus] = mapped_column(
        Enum(WorkflowRuleStatus, name="workflow_rule_status"), default=WorkflowRuleStatus.DRAFT
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class Application(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "applications"

    app_no: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id"))
    application_type: Mapped[ApplicationType] = mapped_column(
        Enum(ApplicationType, name="application_type_code")
    )
    academic_year: Mapped[str] = mapped_column(String(16))
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_rules.id"), nullable=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"), default=ApplicationStatus.DRAFT
    )
    current_stage_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)

    courses: Mapped[list[ApplicationCourse]] = relationship(back_populates="application")
    stages: Mapped[list[StageInstance]] = relationship(
        back_populates="application", order_by="StageInstance.seq"
    )


class ApplicationCourse(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "application_courses"

    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"))
    course_name: Mapped[str] = mapped_column(String(256))
    level: Mapped[str] = mapped_column(String(32))
    existing_intake: Mapped[int] = mapped_column(Integer, default=0)
    proposed_intake: Mapped[int] = mapped_column(Integer, default=0)

    application: Mapped[Application] = relationship(back_populates="courses")


class StageInstance(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "stage_instances"

    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"))
    stage_key: Mapped[str] = mapped_column(String(64))
    seq: Mapped[int] = mapped_column(Integer)
    status: Mapped[StageStatus] = mapped_column(
        Enum(StageStatus, name="stage_status"), default=StageStatus.PENDING
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returns_count: Mapped[int] = mapped_column(Integer, default=0)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    deadline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("deadlines.id"), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    application: Mapped[Application] = relationship(back_populates="stages")


class StageTransition(Base, UUIDPKMixin):
    __tablename__ = "stage_transitions"

    stage_instance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stage_instances.id"))
    from_status: Mapped[str] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Assignment(Base, UUIDPKMixin):
    __tablename__ = "assignments"

    stage_instance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stage_instances.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    # NULL = assigned by the workload balancer; otherwise the regional
    # officer's user id who manually reassigned it (§9.5).
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DeficiencyReason(Base, UUIDPKMixin):
    __tablename__ = "deficiency_reasons"

    code: Mapped[str] = mapped_column(String(64), unique=True)
    label_key: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))


class Deficiency(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "deficiencies"

    stage_instance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stage_instances.id"))
    reason_code: Mapped[str | None] = mapped_column(
        ForeignKey("deficiency_reasons.code"), nullable=True
    )
    custom_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DeficiencyStatus] = mapped_column(
        Enum(DeficiencyStatus, name="deficiency_status"), default=DeficiencyStatus.OPEN
    )
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # FK to `documents` added in Phase P3 once that table exists.
    response_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )


class DeficiencyLetter(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "deficiency_letters"

    stage_instance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stage_instances.id"))
    language: Mapped[str] = mapped_column(String(8), default="en")
    body_md: Mapped[str] = mapped_column(Text)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    edited: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
