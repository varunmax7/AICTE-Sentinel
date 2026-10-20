"""Pydantic request/response shapes for the workflow endpoints (IMPLEMENTATION.md
§13.2, §13.3).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.db.models.enums import ApplicationStatus, ApplicationType, DeadlineStatus, StageStatus


class ApplicationTypeOut(BaseModel):
    code: ApplicationType
    name_key: str
    required_document_types: list[str]


class ApplicationCourseIn(BaseModel):
    course_name: str
    level: str
    existing_intake: int = 0
    proposed_intake: int = 0


class ApplicationCourseOut(ApplicationCourseIn):
    id: str


class ApplicationCreateRequest(BaseModel):
    application_type: ApplicationType
    academic_year: str
    payload: dict[str, Any] = {}
    courses: list[ApplicationCourseIn] = []


class ApplicationUpdateRequest(BaseModel):
    payload: dict[str, Any] | None = None
    courses: list[ApplicationCourseIn] | None = None


class ApplicationOut(BaseModel):
    id: str
    app_no: str | None
    institution_id: str
    application_type: ApplicationType
    academic_year: str
    status: ApplicationStatus
    current_stage_key: str | None
    payload: dict[str, Any]
    submitted_at: datetime | None
    decided_at: datetime | None
    final_decision: str | None
    courses: list[ApplicationCourseOut]


class PrecheckOut(BaseModel):
    """Phase P2 stub — real Document AI pre-check lands in Phase P3 (§14)."""

    status: str = "PENDING_AI"
    message_key: str = "precheck.pendingAi"


class SubmitOtpSendOut(BaseModel):
    sent: bool
    expires_in_seconds: int


class SubmitRequest(BaseModel):
    code: str


class DeadlineOut(BaseModel):
    id: str
    due_at: datetime
    status: DeadlineStatus
    owner_party: str


class StageInstanceOut(BaseModel):
    id: str
    application_id: str
    app_no: str | None
    institution_name: str
    stage_key: str
    seq: int
    status: StageStatus
    activated_at: datetime | None
    completed_at: datetime | None
    returns_count: int
    assigned_user_id: str | None
    deadline: DeadlineOut | None
    allowed_actions: list[str]
    ai_flag_count: int = 0


class DeficiencyIn(BaseModel):
    reason_code: str | None = None
    custom_text: str | None = None


class StageActionRequest(BaseModel):
    action: str
    reason: str | None = None
    deficiencies: list[DeficiencyIn] = []
    letter_body_md: str | None = None


class DeficiencyOut(BaseModel):
    id: str
    reason_code: str | None
    custom_text: str | None
    status: str
    response_text: str | None


class DeficiencyLetterOut(BaseModel):
    id: str
    stage_instance_id: str
    language: str
    body_md: str
    ai_generated: bool
    edited: bool
    sent_at: datetime | None
    sent_by: str | None


class DeficiencyLetterDraftRequest(BaseModel):
    reason: str
    deficiencies: list[DeficiencyIn] = []


class DeficiencyLetterUpdateRequest(BaseModel):
    body_md: str


class ResubmitResponseIn(BaseModel):
    deficiency_id: str
    response_text: str


class ResubmitRequest(BaseModel):
    responses: list[ResubmitResponseIn]


class ReassignRequest(BaseModel):
    user_id: str
    reason: str


class TimelineEntryOut(BaseModel):
    id: str
    actor: str
    action: str
    at: datetime
    channel: str | None = None
