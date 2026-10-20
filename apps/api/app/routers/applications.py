"""Applications endpoints (IMPLEMENTATION.md §13.2). Document AI pre-check
(§14) and communications (§13.4/§11, Phase P7) are stubbed per the Phase P2
task list; everything else here is real.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import clock
from app.core.deps import get_current_user, require
from app.db.models.audit import AuditEvent
from app.db.models.deadline import Deadline
from app.db.models.enums import ActorType, ApplicationStatus, OtpPurpose, UserRole
from app.db.models.institution import Institution
from app.db.models.user import User
from app.db.models.workflow import Application, ApplicationCourse, StageInstance, StageTransition
from app.db.session import get_db
from app.schemas.workflow import (
    ApplicationCourseOut,
    ApplicationCreateRequest,
    ApplicationOut,
    ApplicationUpdateRequest,
    PrecheckOut,
    ResubmitRequest,
    StageInstanceOut,
    SubmitOtpSendOut,
    SubmitRequest,
    TimelineEntryOut,
)
from app.services.audit.chain import write_audit_event
from app.services.auth.action_otp import send_action_otp, verify_action_otp
from app.services.events import emit_event, trigger_publish
from app.services.workflow.deadlines import close_deadline
from app.services.workflow.engine import WorkflowError, route
from app.services.workflow.engine import resubmit as engine_resubmit
from app.services.workflow.presenters import stage_instance_out
from app.services.workflow.rules import resolve_published_rule
from app.services.workflow.scope import institution_in_scope, scoped_region_ids

router = APIRouter(tags=["applications"])

WORKFLOW_ERROR_STATUS: dict[str, int] = {
    "ROLE_NOT_ALLOWED": status.HTTP_403_FORBIDDEN,
    "OUT_OF_REGION": status.HTTP_403_FORBIDDEN,
    "STAGE_NOT_ASSIGNED_TO_YOU": status.HTTP_403_FORBIDDEN,
}


def _raise_workflow_error(exc: WorkflowError) -> None:
    raise HTTPException(
        WORKFLOW_ERROR_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "params": exc.params},
    ) from exc


def _to_out(application: Application) -> ApplicationOut:
    return ApplicationOut(
        id=str(application.id),
        app_no=application.app_no,
        institution_id=str(application.institution_id),
        application_type=application.application_type,
        academic_year=application.academic_year,
        status=application.status,
        current_stage_key=application.current_stage_key,
        payload=application.payload,
        submitted_at=application.submitted_at,
        decided_at=application.decided_at,
        final_decision=application.final_decision,
        courses=[
            ApplicationCourseOut(
                id=str(c.id),
                course_name=c.course_name,
                level=c.level,
                existing_intake=c.existing_intake,
                proposed_intake=c.proposed_intake,
            )
            for c in application.courses
        ],
    )


async def _get_scoped_application(
    db: AsyncSession, user: User, application_id: uuid.UUID
) -> Application:
    application = await db.get(Application, application_id)
    if application is None or not await institution_in_scope(db, user, application.institution_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "APPLICATION_NOT_FOUND"})
    return application


async def _generate_app_no(db: AsyncSession) -> str:
    year = clock.now().year
    prefix = f"APP-{year}-"
    count = await db.scalar(
        select(func.count()).select_from(Application).where(Application.app_no.like(f"{prefix}%"))
    )
    return f"{prefix}{(count or 0) + 1:04d}"


@router.get("/applications", response_model=list[ApplicationOut])
async def list_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ApplicationOut]:
    query = select(Application).options(selectinload(Application.courses))
    if user.role == UserRole.INSTITUTION:
        query = query.where(Application.institution_id == user.institution_id)
    else:
        region_ids = await scoped_region_ids(db, user)
        if region_ids is not None:
            query = query.join(Institution, Institution.id == Application.institution_id).where(
                Institution.region_id.in_(region_ids)
            )
    query = (
        query.order_by(Application.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return [_to_out(a) for a in result.scalars().unique()]


@router.post("/applications", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_application(
    body: ApplicationCreateRequest,
    user: User = Depends(require(UserRole.INSTITUTION)),
    db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    application = Application(
        institution_id=user.institution_id,
        application_type=body.application_type,
        academic_year=body.academic_year,
        status=ApplicationStatus.DRAFT,
        payload=body.payload,
    )
    db.add(application)
    await db.flush()
    for course in body.courses:
        db.add(ApplicationCourse(application_id=application.id, **course.model_dump()))
    await db.commit()
    await db.refresh(application, attribute_names=["courses"])
    return _to_out(application)


@router.get("/applications/{application_id}", response_model=ApplicationOut)
async def get_application(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    application = await _get_scoped_application(db, user, application_id)
    await db.refresh(application, attribute_names=["courses"])
    return _to_out(application)


@router.get("/applications/{application_id}/stages", response_model=list[StageInstanceOut])
async def get_application_stages(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StageInstanceOut]:
    """Backs the application-detail horizontal stepper (§15.2) — not an
    endpoint named explicitly in §13.2, but the natural sub-resource for it.
    """

    application = await _get_scoped_application(db, user, application_id)
    result = await db.execute(
        select(StageInstance)
        .where(StageInstance.application_id == application.id)
        .order_by(StageInstance.seq)
    )
    return [await stage_instance_out(db, s) for s in result.scalars()]


@router.patch("/applications/{application_id}", response_model=ApplicationOut)
async def update_application(
    application_id: uuid.UUID,
    body: ApplicationUpdateRequest,
    user: User = Depends(require(UserRole.INSTITUTION)),
    db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    application = await _get_scoped_application(db, user, application_id)
    if application.status != ApplicationStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "APPLICATION_NOT_DRAFT"})

    if body.payload is not None:
        application.payload = body.payload
    if body.courses is not None:
        await db.execute(
            delete(ApplicationCourse).where(ApplicationCourse.application_id == application.id)
        )
        for course in body.courses:
            db.add(ApplicationCourse(application_id=application.id, **course.model_dump()))

    await db.commit()
    await db.refresh(application, attribute_names=["courses"])
    return _to_out(application)


@router.post("/applications/{application_id}/precheck", response_model=PrecheckOut)
async def precheck_application(
    application_id: uuid.UUID,
    user: User = Depends(require(UserRole.INSTITUTION)),
    db: AsyncSession = Depends(get_db),
) -> PrecheckOut:
    await _get_scoped_application(db, user, application_id)
    return PrecheckOut()


@router.post("/applications/{application_id}/submit/otp", response_model=SubmitOtpSendOut)
async def send_submit_otp(
    application_id: uuid.UUID,
    user: User = Depends(require(UserRole.INSTITUTION)),
    db: AsyncSession = Depends(get_db),
) -> SubmitOtpSendOut:
    application = await _get_scoped_application(db, user, application_id)
    if application.status != ApplicationStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "APPLICATION_NOT_DRAFT"})
    await send_action_otp(db, user, purpose=OtpPurpose.ESIGN)
    return SubmitOtpSendOut(sent=True, expires_in_seconds=600)


@router.post("/applications/{application_id}/submit", response_model=ApplicationOut)
async def submit_application(
    application_id: uuid.UUID,
    body: SubmitRequest,
    user: User = Depends(require(UserRole.INSTITUTION)),
    db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    application = await _get_scoped_application(db, user, application_id)
    if application.status != ApplicationStatus.DRAFT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "APPLICATION_NOT_DRAFT"})

    if not await verify_action_otp(db, user, purpose=OtpPurpose.ESIGN, code=body.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_OTP"})

    rule = await resolve_published_rule(
        db, application_type=application.application_type, academic_year=application.academic_year
    )
    if rule is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"code": "RULE_NOT_PUBLISHED"})

    application.rule_id = rule.id
    application.app_no = await _generate_app_no(db)
    application.status = ApplicationStatus.SUBMITTED
    application.submitted_at = clock.now()
    await db.flush()

    await write_audit_event(
        db,
        actor_type=ActorType.USER,
        actor_id=str(user.id),
        action="application.submit",
        entity_type="application",
        entity_id=application.id,
        application_id=application.id,
    )
    await emit_event(
        db,
        "application.submitted",
        {"application_id": str(application.id), "app_no": application.app_no},
    )
    await db.commit()
    trigger_publish()

    try:
        await route(db, application)
    except WorkflowError as exc:
        _raise_workflow_error(exc)

    await db.refresh(application, attribute_names=["courses"])
    return _to_out(application)


@router.post("/applications/{application_id}/withdraw", response_model=ApplicationOut)
async def withdraw_application(
    application_id: uuid.UUID,
    user: User = Depends(require(UserRole.INSTITUTION)),
    db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    application = await _get_scoped_application(db, user, application_id)
    if application.status not in (ApplicationStatus.SUBMITTED, ApplicationStatus.IN_PROCESS):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail={"code": "APPLICATION_NOT_WITHDRAWABLE"}
        )

    stages_result = await db.execute(
        select(StageInstance).where(
            StageInstance.application_id == application.id, StageInstance.deadline_id.is_not(None)
        )
    )
    for stage in stages_result.scalars():
        deadline = await db.get(Deadline, stage.deadline_id)
        if deadline is not None:
            close_deadline(deadline)

    application.status = ApplicationStatus.WITHDRAWN
    await write_audit_event(
        db,
        actor_type=ActorType.USER,
        actor_id=str(user.id),
        action="application.withdraw",
        entity_type="application",
        entity_id=application.id,
        application_id=application.id,
    )
    await emit_event(db, "application.withdrawn", {"application_id": str(application.id)})
    await db.commit()
    trigger_publish()

    await db.refresh(application, attribute_names=["courses"])
    return _to_out(application)


@router.post("/applications/{application_id}/resubmit", response_model=ApplicationOut)
async def resubmit_application(
    application_id: uuid.UUID,
    body: ResubmitRequest,
    user: User = Depends(require(UserRole.INSTITUTION)),
    db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    application = await _get_scoped_application(db, user, application_id)
    try:
        await engine_resubmit(
            db, application, actor=user, responses=[r.model_dump() for r in body.responses]
        )
    except WorkflowError as exc:
        _raise_workflow_error(exc)

    await db.refresh(application, attribute_names=["courses"])
    return _to_out(application)


@router.get("/applications/{application_id}/timeline", response_model=list[TimelineEntryOut])
async def get_application_timeline(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TimelineEntryOut]:
    application = await _get_scoped_application(db, user, application_id)

    transitions_result = await db.execute(
        select(StageTransition)
        .join(StageInstance, StageTransition.stage_instance_id == StageInstance.id)
        .where(StageInstance.application_id == application.id)
    )

    entries: list[tuple[datetime, TimelineEntryOut]] = []
    for row in transitions_result.scalars().unique():
        entries.append(
            (
                row.at,
                TimelineEntryOut(
                    id=str(row.id),
                    actor=str(row.actor_id) if row.actor_id else "System",
                    action=f"{row.action}: {row.from_status} → {row.to_status}",
                    at=row.at,
                    channel=None,
                ),
            )
        )

    audit_result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.application_id == application.id)
        .order_by(AuditEvent.id)
    )
    for ev in audit_result.scalars():
        entries.append(
            (
                ev.occurred_at,
                TimelineEntryOut(
                    id=f"audit-{ev.id}",
                    actor=ev.actor_id or ev.actor_type.value,
                    action=ev.action,
                    at=ev.occurred_at,
                    channel=ev.channel,
                ),
            )
        )

    entries.sort(key=lambda pair: pair[0])
    return [entry for _at, entry in entries]


@router.get("/applications/{application_id}/communications", response_model=list[dict[str, Any]])
async def get_application_communications(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Stub — the notification orchestrator (emails/WhatsApp/calls) that
    populates this is Phase P7.
    """

    await _get_scoped_application(db, user, application_id)
    return []
