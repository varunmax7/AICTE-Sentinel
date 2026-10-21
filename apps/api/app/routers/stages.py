"""Stage & officer-work endpoints (IMPLEMENTATION.md §13.3): the officer
queue, stage detail + actions, and the deficiency-letter draft/edit/send
flow (§9.6).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import now
from app.core.deps import get_current_user, require, user_region_ids
from app.db.models.enums import ActorType, StageStatus, UserRole
from app.db.models.institution import Institution
from app.db.models.user import User
from app.db.models.workflow import (
    Application,
    Assignment,
    Deficiency,
    DeficiencyLetter,
    StageInstance,
)
from app.db.session import get_db
from app.routers.applications import WORKFLOW_ERROR_STATUS
from app.schemas.workflow import (
    DeficiencyLetterDraftRequest,
    DeficiencyLetterOut,
    DeficiencyLetterUpdateRequest,
    DeficiencyOut,
    ReassignRequest,
    StageActionRequest,
    StageInstanceOut,
)
from app.services.audit.chain import write_audit_event
from app.services.events import emit_event, trigger_publish
from app.services.workflow.assignment import assign
from app.services.workflow.engine import WorkflowError, perform_action
from app.services.workflow.letters import draft_deficiency_letter_body
from app.services.workflow.presenters import stage_instance_out
from app.services.workflow.scope import institution_in_scope

router = APIRouter(tags=["stages"])

OFFICER_ROLES = (
    UserRole.SCRUTINY_OFFICER,
    UserRole.REGIONAL_OFFICER,
    UserRole.COMMITTEE_MEMBER,
    UserRole.EVC_EXPERT,
)


async def _get_scoped_stage(db: AsyncSession, user: User, stage_id: uuid.UUID) -> StageInstance:
    stage = await db.get(StageInstance, stage_id)
    if stage is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "STAGE_NOT_FOUND"})
    application = await db.get(Application, stage.application_id)
    if application is None or not await institution_in_scope(db, user, application.institution_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "STAGE_NOT_FOUND"})
    return stage


@router.get("/queue", response_model=list[StageInstanceOut])
async def get_queue(
    user: User = Depends(require(*OFFICER_ROLES)), db: AsyncSession = Depends(get_db)
) -> list[StageInstanceOut]:
    result = await db.execute(
        select(StageInstance).where(
            StageInstance.assigned_user_id == user.id, StageInstance.status == StageStatus.ACTIVE
        )
    )
    stages = list(result.scalars())
    outs = [await stage_instance_out(db, s) for s in stages]
    outs.sort(key=lambda o: o.deadline.due_at if o.deadline else now())
    return outs


@router.get("/stages/{stage_id}", response_model=StageInstanceOut)
async def get_stage(
    stage_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> StageInstanceOut:
    stage = await _get_scoped_stage(db, user, stage_id)
    return await stage_instance_out(db, stage)


@router.post("/stages/{stage_id}/actions", response_model=StageInstanceOut)
async def perform_stage_action(
    stage_id: uuid.UUID,
    body: StageActionRequest,
    user: User = Depends(require(*OFFICER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> StageInstanceOut:
    stage = await _get_scoped_stage(db, user, stage_id)
    try:
        stage = await perform_action(
            db,
            stage,
            action=body.action,
            actor=user,
            reason=body.reason,
            deficiencies=[d.model_dump() for d in body.deficiencies],
            letter_body_md=body.letter_body_md,
        )
    except WorkflowError as exc:
        raise HTTPException(
            WORKFLOW_ERROR_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
            detail={"code": exc.code, "params": exc.params},
        ) from exc
    return await stage_instance_out(db, stage)


@router.get("/stages/{stage_id}/deficiencies", response_model=list[DeficiencyOut])
async def list_stage_deficiencies(
    stage_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[DeficiencyOut]:
    await _get_scoped_stage(db, user, stage_id)
    result = await db.execute(select(Deficiency).where(Deficiency.stage_instance_id == stage_id))
    return [
        DeficiencyOut(
            id=str(d.id),
            reason_code=d.reason_code,
            custom_text=d.custom_text,
            status=d.status.value,
            response_text=d.response_text,
        )
        for d in result.scalars()
    ]


@router.post("/stages/{stage_id}/deficiency-letter/draft", response_model=DeficiencyLetterOut)
async def draft_deficiency_letter(
    stage_id: uuid.UUID,
    body: DeficiencyLetterDraftRequest,
    user: User = Depends(require(*OFFICER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> DeficiencyLetterOut:
    stage = await _get_scoped_stage(db, user, stage_id)
    application = await db.get(Application, stage.application_id)
    assert application is not None
    institution = await db.get(Institution, application.institution_id)
    assert institution is not None

    body_md = await draft_deficiency_letter_body(
        institution_name=institution.name,
        app_no=application.app_no,
        reason=body.reason,
        deficiencies=[d.custom_text or d.reason_code or "" for d in body.deficiencies],
    )
    letter = DeficiencyLetter(stage_instance_id=stage.id, body_md=body_md, ai_generated=True)
    db.add(letter)
    await db.commit()
    await db.refresh(letter)
    return DeficiencyLetterOut(
        id=str(letter.id),
        stage_instance_id=str(letter.stage_instance_id),
        language=letter.language,
        body_md=letter.body_md,
        ai_generated=letter.ai_generated,
        edited=letter.edited,
        sent_at=letter.sent_at,
        sent_by=str(letter.sent_by) if letter.sent_by else None,
    )


async def _get_scoped_letter(
    db: AsyncSession, user: User, letter_id: uuid.UUID
) -> DeficiencyLetter:
    letter = await db.get(DeficiencyLetter, letter_id)
    if letter is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "LETTER_NOT_FOUND"})
    await _get_scoped_stage(db, user, letter.stage_instance_id)
    return letter


@router.put("/deficiency-letters/{letter_id}", response_model=DeficiencyLetterOut)
async def update_deficiency_letter(
    letter_id: uuid.UUID,
    body: DeficiencyLetterUpdateRequest,
    user: User = Depends(require(*OFFICER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> DeficiencyLetterOut:
    letter = await _get_scoped_letter(db, user, letter_id)
    if letter.sent_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "LETTER_ALREADY_SENT"})
    letter.body_md = body.body_md
    letter.edited = True
    await db.commit()
    await db.refresh(letter)
    return DeficiencyLetterOut(
        id=str(letter.id),
        stage_instance_id=str(letter.stage_instance_id),
        language=letter.language,
        body_md=letter.body_md,
        ai_generated=letter.ai_generated,
        edited=letter.edited,
        sent_at=letter.sent_at,
        sent_by=str(letter.sent_by) if letter.sent_by else None,
    )


@router.post("/deficiency-letters/{letter_id}/send", response_model=DeficiencyLetterOut)
async def send_deficiency_letter(
    letter_id: uuid.UUID,
    user: User = Depends(require(*OFFICER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> DeficiencyLetterOut:
    letter = await _get_scoped_letter(db, user, letter_id)
    if letter.sent_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "LETTER_ALREADY_SENT"})

    letter.sent_at = now()
    letter.sent_by = user.id
    await write_audit_event(
        db,
        actor_type=ActorType.USER,
        actor_id=str(user.id),
        action="deficiency_letter.sent",
        entity_type="deficiency_letter",
        entity_id=letter.id,
    )
    await emit_event(
        db,
        "deficiency_letter.sent",
        {"letter_id": str(letter.id), "stage_instance_id": str(letter.stage_instance_id)},
    )
    await db.commit()
    trigger_publish()
    await db.refresh(letter)
    return DeficiencyLetterOut(
        id=str(letter.id),
        stage_instance_id=str(letter.stage_instance_id),
        language=letter.language,
        body_md=letter.body_md,
        ai_generated=letter.ai_generated,
        edited=letter.edited,
        sent_at=letter.sent_at,
        sent_by=str(letter.sent_by) if letter.sent_by else None,
    )


@router.post("/assignments/{assignment_id}/reassign", response_model=StageInstanceOut)
async def reassign_assignment(
    assignment_id: uuid.UUID,
    body: ReassignRequest,
    user: User = Depends(require(UserRole.REGIONAL_OFFICER)),
    db: AsyncSession = Depends(get_db),
) -> StageInstanceOut:
    assignment = await db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "ASSIGNMENT_NOT_FOUND"})

    stage = await db.get(StageInstance, assignment.stage_instance_id)
    if stage is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "STAGE_NOT_FOUND"})
    application = await db.get(Application, stage.application_id)
    assert application is not None
    institution = await db.get(Institution, application.institution_id)
    assert institution is not None

    region_ids = await user_region_ids(db, user)
    if region_ids is not None and institution.region_id not in region_ids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "OUT_OF_REGION"})

    new_user = await db.get(User, uuid.UUID(body.user_id))
    if new_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "USER_NOT_FOUND"})

    await assign(db, stage, new_user, assigned_by_user_id=user.id, reason=body.reason)
    await write_audit_event(
        db,
        actor_type=ActorType.USER,
        actor_id=str(user.id),
        action="assignment.reassign",
        entity_type="stage_instance",
        entity_id=stage.id,
        application_id=application.id,
        reason=body.reason,
        after={"assigned_user_id": str(new_user.id)},
    )
    await emit_event(
        db,
        "assignment.reassigned",
        {"stage_instance_id": str(stage.id), "assigned_user_id": str(new_user.id)},
    )
    await db.commit()
    trigger_publish()
    await db.refresh(stage)
    return await stage_instance_out(db, stage)
