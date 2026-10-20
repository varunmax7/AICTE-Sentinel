"""Workflow engine (IMPLEMENTATION.md §9.4): `route`, `perform_action`,
`advance`, `resubmit`. Every transition locks nothing beyond the normal
per-request transaction (Phase P2 has no concurrent-actor contention worth a
row lock yet — `SELECT … FOR UPDATE` on the application can be added
alongside real concurrency load later without changing these signatures),
validates against the rule, updates stage + application state, creates or
resolves the stage's deadline, writes one `stage_transitions` row, one
`audit_events` row and one `outbox_events` row, then commits exactly once.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import now
from app.core.deps import user_region_ids
from app.db.models.deadline import Deadline
from app.db.models.enums import (
    ActorType,
    ApplicationStatus,
    DeadlineOwnerParty,
    DeficiencyStatus,
    StageStatus,
)
from app.db.models.institution import Institution
from app.db.models.user import User
from app.db.models.workflow import (
    Application,
    Deficiency,
    DeficiencyLetter,
    StageInstance,
    StageTransition,
    WorkflowRule,
)
from app.services.audit.chain import write_audit_event
from app.services.events import emit_event, trigger_publish
from app.services.workflow.assignment import assign, pick_assignee
from app.services.workflow.calendar import due_at_for_sla
from app.services.workflow.conditions import evaluate_branch_condition
from app.services.workflow.deadlines import close_deadline, pause_deadline, resume_deadline
from app.services.workflow.letters import render_deficiency_letter_stub
from app.services.workflow.rules import RuleDefinition, StageDef, validate_rule_definition


class WorkflowError(Exception):
    def __init__(self, code: str, params: dict[str, Any] | None = None) -> None:
        self.code = code
        self.params = params or {}
        super().__init__(code)


async def _load_rule(db: AsyncSession, application: Application) -> RuleDefinition:
    if application.rule_id is None:
        raise WorkflowError("RULE_NOT_RESOLVED")
    rule_row = await db.get(WorkflowRule, application.rule_id)
    if rule_row is None:
        raise WorkflowError("RULE_NOT_FOUND")
    return validate_rule_definition(rule_row.definition)


def _is_skipped(rule: RuleDefinition, stage_def: StageDef, application: Application) -> bool:
    for branch in rule.branches:
        matched = evaluate_branch_condition(
            branch.when, application_payload=application.payload, stage_key=stage_def.key
        )
        if matched and branch.skip:
            return True
    return False


async def _activate_stage(
    db: AsyncSession,
    *,
    application: Application,
    institution: Institution,
    stage_instance: StageInstance,
    stage_def: StageDef,
) -> None:
    from_status = stage_instance.status
    stage_instance.status = StageStatus.ACTIVE
    stage_instance.activated_at = now()
    application.current_stage_key = stage_instance.stage_key

    if stage_def.kind == "HUMAN":
        due_at = await due_at_for_sla(
            db,
            start=now(),
            sla_days=stage_def.sla_days,
            sla_calendar=stage_def.sla_calendar,
            region_id=institution.region_id,
        )
        deadline = Deadline(
            subject_type="stage_instance",
            subject_id=stage_instance.id,
            institution_id=institution.id,
            application_id=application.id,
            due_at=due_at,
            policy_key=stage_def.escalation_policy,
        )
        db.add(deadline)
        await db.flush()
        stage_instance.deadline_id = deadline.id

        assignee = await pick_assignee(db, role=stage_def.role, region_id=institution.region_id)  # type: ignore[arg-type]
        if assignee is not None:
            await assign(db, stage_instance, assignee)

    db.add(
        StageTransition(
            stage_instance_id=stage_instance.id,
            from_status=from_status.value,
            to_status=StageStatus.ACTIVE.value,
            action="ACTIVATE",
            actor_id=None,
            at=now(),
        )
    )
    await write_audit_event(
        db,
        actor_type=ActorType.SYSTEM,
        actor_id=None,
        action="stage.activated",
        entity_type="stage_instance",
        entity_id=stage_instance.id,
        application_id=application.id,
        after={"stage_key": stage_instance.stage_key},
    )
    await emit_event(
        db,
        "stage.activated",
        {
            "application_id": str(application.id),
            "stage_instance_id": str(stage_instance.id),
            "stage_key": stage_instance.stage_key,
            "assigned_user_id": str(stage_instance.assigned_user_id)
            if stage_instance.assigned_user_id
            else None,
        },
    )
    await db.flush()


async def _complete_stage(
    db: AsyncSession,
    *,
    application: Application,
    stage_instance: StageInstance,
    action: str,
    actor: User | None,
    reason: str | None,
) -> None:
    from_status = stage_instance.status
    stage_instance.status = StageStatus.COMPLETED
    stage_instance.completed_at = now()
    if stage_instance.deadline_id:
        deadline = await db.get(Deadline, stage_instance.deadline_id)
        if deadline is not None:
            close_deadline(deadline)

    db.add(
        StageTransition(
            stage_instance_id=stage_instance.id,
            from_status=from_status.value,
            to_status=StageStatus.COMPLETED.value,
            action=action,
            actor_id=actor.id if actor else None,
            reason=reason,
            at=now(),
        )
    )
    await write_audit_event(
        db,
        actor_type=ActorType.USER if actor else ActorType.SYSTEM,
        actor_id=str(actor.id) if actor else None,
        action=f"stage.{action.lower()}",
        entity_type="stage_instance",
        entity_id=stage_instance.id,
        application_id=application.id,
        reason=reason,
    )
    await emit_event(
        db,
        "stage.completed",
        {
            "application_id": str(application.id),
            "stage_instance_id": str(stage_instance.id),
            "stage_key": stage_instance.stage_key,
        },
    )
    await db.flush()


async def _activate_next(
    db: AsyncSession,
    *,
    application: Application,
    rule: RuleDefinition,
    institution: Institution,
    after_seq: int,
) -> None:
    result = await db.execute(
        select(StageInstance)
        .where(StageInstance.application_id == application.id, StageInstance.seq > after_seq)
        .order_by(StageInstance.seq)
    )
    stage_instances = list(result.scalars())

    for stage_instance in stage_instances:
        if stage_instance.status == StageStatus.SKIPPED:
            continue
        if stage_instance.status != StageStatus.PENDING:
            return

        stage_def = rule.stage(stage_instance.stage_key)
        await _activate_stage(
            db,
            application=application,
            institution=institution,
            stage_instance=stage_instance,
            stage_def=stage_def,
        )
        if stage_def.kind == "SYSTEM" and stage_def.auto_complete:
            await _complete_stage(
                db,
                application=application,
                stage_instance=stage_instance,
                action="AUTO_COMPLETE",
                actor=None,
                reason=None,
            )
            continue
        return

    application.current_stage_key = None
    application.status = ApplicationStatus.DECISION_RECORDED
    application.decided_at = now()
    await db.flush()


async def route(db: AsyncSession, application: Application) -> None:
    """Called on submit: loads the resolved rule, creates every stage
    instance up front (seq order, branches evaluated once against the
    submitted payload), then activates/auto-completes from the start.
    """

    rule = await _load_rule(db, application)
    institution = await db.get(Institution, application.institution_id)
    if institution is None:
        raise WorkflowError("INSTITUTION_NOT_FOUND")

    for seq, stage_def in enumerate(rule.stages):
        skipped = _is_skipped(rule, stage_def, application)
        db.add(
            StageInstance(
                application_id=application.id,
                stage_key=stage_def.key,
                seq=seq,
                status=StageStatus.SKIPPED if skipped else StageStatus.PENDING,
            )
        )
    await db.flush()

    application.status = ApplicationStatus.IN_PROCESS
    await db.flush()

    await _activate_next(
        db, application=application, rule=rule, institution=institution, after_seq=-1
    )
    await db.commit()
    trigger_publish()


async def advance(db: AsyncSession, application: Application) -> None:
    """Activates the next non-skipped stage after the application's current
    one, or records the decision if none remain. Does not commit — callers
    (`perform_action`, tests) own the transaction boundary.
    """

    rule = await _load_rule(db, application)
    institution = await db.get(Institution, application.institution_id)
    if institution is None:
        raise WorkflowError("INSTITUTION_NOT_FOUND")

    after_seq = -1
    if application.current_stage_key is not None:
        result = await db.execute(
            select(StageInstance).where(
                StageInstance.application_id == application.id,
                StageInstance.stage_key == application.current_stage_key,
            )
        )
        current = result.scalar_one_or_none()
        if current is not None:
            after_seq = current.seq

    await _activate_next(
        db, application=application, rule=rule, institution=institution, after_seq=after_seq
    )


_COMPLETING_ACTIONS = {"CLEAR", "COMPLETE"}


async def perform_action(
    db: AsyncSession,
    stage_instance: StageInstance,
    *,
    action: str,
    actor: User,
    reason: str | None = None,
    deficiencies: list[dict[str, str | None]] | None = None,
    letter_body_md: str | None = None,
) -> StageInstance:
    application = await db.get(Application, stage_instance.application_id)
    if application is None:
        raise WorkflowError("APPLICATION_NOT_FOUND")
    institution = await db.get(Institution, application.institution_id)
    if institution is None:
        raise WorkflowError("INSTITUTION_NOT_FOUND")
    rule = await _load_rule(db, application)
    stage_def = rule.stage(stage_instance.stage_key)

    if stage_instance.status != StageStatus.ACTIVE:
        raise WorkflowError("STAGE_NOT_ACTIVE", {"status": stage_instance.status.value})
    if action not in stage_def.actions:
        raise WorkflowError(
            "STAGE_ACTION_NOT_ALLOWED", {"action": action, "allowed": stage_def.actions}
        )
    if stage_def.role is not None and actor.role != stage_def.role:
        raise WorkflowError("ROLE_NOT_ALLOWED", {"required": stage_def.role.value})

    region_ids = await user_region_ids(db, actor)
    if region_ids is not None and institution.region_id not in region_ids:
        raise WorkflowError("OUT_OF_REGION")
    if (
        region_ids is not None
        and stage_instance.assigned_user_id is not None
        and stage_instance.assigned_user_id != actor.id
    ):
        raise WorkflowError("STAGE_NOT_ASSIGNED_TO_YOU")

    if action in _COMPLETING_ACTIONS:
        await _complete_stage(
            db,
            application=application,
            stage_instance=stage_instance,
            action=action,
            actor=actor,
            reason=reason,
        )
        if stage_def.auto_advance_on_clear:
            await advance(db, application)

    elif action == "RETURN":
        if not deficiencies:
            raise WorkflowError("DEFICIENCY_REQUIRED")
        if not reason:
            raise WorkflowError("REASON_REQUIRED")
        max_returns_exceeded = (
            stage_def.max_returns is not None
            and stage_instance.returns_count >= stage_def.max_returns
        )

        from_status = stage_instance.status
        stage_instance.status = StageStatus.RETURNED
        stage_instance.returns_count += 1

        for d in deficiencies:
            db.add(
                Deficiency(
                    stage_instance_id=stage_instance.id,
                    reason_code=d.get("reason_code"),
                    custom_text=d.get("custom_text"),
                )
            )

        letter_body = letter_body_md or render_deficiency_letter_stub(
            institution_name=institution.name,
            app_no=application.app_no,
            reason=reason,
            deficiencies=[d.get("custom_text") or d.get("reason_code") or "" for d in deficiencies],
        )
        db.add(
            DeficiencyLetter(
                stage_instance_id=stage_instance.id,
                body_md=letter_body,
                ai_generated=letter_body_md is None,
            )
        )

        if stage_instance.deadline_id:
            deadline = await db.get(Deadline, stage_instance.deadline_id)
            if deadline is not None:
                pause_deadline(deadline, new_owner=DeadlineOwnerParty.INSTITUTION)

        db.add(
            StageTransition(
                stage_instance_id=stage_instance.id,
                from_status=from_status.value,
                to_status=StageStatus.RETURNED.value,
                action="RETURN",
                actor_id=actor.id,
                reason=reason,
                payload={
                    "deficiencies": deficiencies,
                    "max_returns_exceeded": max_returns_exceeded,
                },
                at=now(),
            )
        )
        await write_audit_event(
            db,
            actor_type=ActorType.USER,
            actor_id=str(actor.id),
            action="stage.return",
            entity_type="stage_instance",
            entity_id=stage_instance.id,
            application_id=application.id,
            reason=reason,
        )
        await emit_event(
            db,
            "stage.returned",
            {
                "application_id": str(application.id),
                "stage_instance_id": str(stage_instance.id),
                "max_returns_exceeded": max_returns_exceeded,
            },
        )
        await db.flush()

    elif action == "REQUEST_CLARIFICATION":
        if not reason:
            raise WorkflowError("REASON_REQUIRED")
        if stage_instance.deadline_id:
            deadline = await db.get(Deadline, stage_instance.deadline_id)
            if deadline is not None:
                pause_deadline(deadline, new_owner=DeadlineOwnerParty.INSTITUTION)
        db.add(
            StageTransition(
                stage_instance_id=stage_instance.id,
                from_status=stage_instance.status.value,
                to_status=stage_instance.status.value,
                action="REQUEST_CLARIFICATION",
                actor_id=actor.id,
                reason=reason,
                at=now(),
            )
        )
        await write_audit_event(
            db,
            actor_type=ActorType.USER,
            actor_id=str(actor.id),
            action="stage.request_clarification",
            entity_type="stage_instance",
            entity_id=stage_instance.id,
            application_id=application.id,
            reason=reason,
        )
        await emit_event(
            db,
            "stage.clarification_requested",
            {"application_id": str(application.id), "stage_instance_id": str(stage_instance.id)},
        )
        await db.flush()

    elif action == "REFER_SENIOR":
        if not reason:
            raise WorkflowError("REASON_REQUIRED")
        db.add(
            StageTransition(
                stage_instance_id=stage_instance.id,
                from_status=stage_instance.status.value,
                to_status=stage_instance.status.value,
                action="REFER_SENIOR",
                actor_id=actor.id,
                reason=reason,
                at=now(),
            )
        )
        await write_audit_event(
            db,
            actor_type=ActorType.USER,
            actor_id=str(actor.id),
            action="stage.refer_senior",
            entity_type="stage_instance",
            entity_id=stage_instance.id,
            application_id=application.id,
            reason=reason,
        )
        await emit_event(
            db,
            "stage.referred",
            {"application_id": str(application.id), "stage_instance_id": str(stage_instance.id)},
        )
        await db.flush()

    else:
        raise WorkflowError("ACTION_NOT_IMPLEMENTED", {"action": action})

    await db.commit()
    trigger_publish()
    await db.refresh(stage_instance)
    return stage_instance


async def resubmit(
    db: AsyncSession, application: Application, *, actor: User, responses: list[dict[str, Any]]
) -> StageInstance:
    result = await db.execute(
        select(StageInstance)
        .where(
            StageInstance.application_id == application.id,
            StageInstance.status == StageStatus.RETURNED,
        )
        .order_by(StageInstance.seq.desc())
        .limit(1)
    )
    stage_instance = result.scalar_one_or_none()
    if stage_instance is None:
        raise WorkflowError("NO_RETURNED_STAGE")

    deficiency_ids = {
        uuid.UUID(str(r["deficiency_id"])) for r in responses if r.get("deficiency_id")
    }
    if deficiency_ids:
        deficiency_rows = await db.execute(
            select(Deficiency).where(
                Deficiency.stage_instance_id == stage_instance.id, Deficiency.id.in_(deficiency_ids)
            )
        )
        by_id = {d.id: d for d in deficiency_rows.scalars()}
        for r in responses:
            d = by_id.get(uuid.UUID(str(r["deficiency_id"]))) if r.get("deficiency_id") else None
            if d is None:
                continue
            d.response_text = r.get("response_text")
            d.status = DeficiencyStatus.RESPONDED

    from_status = stage_instance.status
    stage_instance.status = StageStatus.ACTIVE
    if stage_instance.deadline_id:
        deadline = await db.get(Deadline, stage_instance.deadline_id)
        if deadline is not None:
            resume_deadline(deadline, new_owner=DeadlineOwnerParty.OFFICER)

    db.add(
        StageTransition(
            stage_instance_id=stage_instance.id,
            from_status=from_status.value,
            to_status=StageStatus.ACTIVE.value,
            action="RESUBMIT",
            actor_id=actor.id,
            payload={"responses": responses},
            at=now(),
        )
    )
    await write_audit_event(
        db,
        actor_type=ActorType.USER,
        actor_id=str(actor.id),
        action="application.resubmit",
        entity_type="application",
        entity_id=application.id,
        application_id=application.id,
    )
    await emit_event(
        db,
        "application.resubmitted",
        {"application_id": str(application.id), "stage_instance_id": str(stage_instance.id)},
    )
    await db.flush()
    await db.commit()
    trigger_publish()
    await db.refresh(stage_instance)
    return stage_instance
