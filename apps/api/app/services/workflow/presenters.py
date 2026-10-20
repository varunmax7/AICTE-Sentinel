"""Shared read-model builders used by both the applications and stages
routers (kept out of either router module to avoid a circular import
between them).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.deadline import Deadline
from app.db.models.enums import StageStatus
from app.db.models.institution import Institution
from app.db.models.workflow import Application, StageInstance, WorkflowRule
from app.schemas.workflow import DeadlineOut, StageInstanceOut
from app.services.workflow.rules import validate_rule_definition


async def stage_instance_out(db: AsyncSession, stage: StageInstance) -> StageInstanceOut:
    application = await db.get(Application, stage.application_id)
    assert application is not None
    institution = await db.get(Institution, application.institution_id)
    assert institution is not None

    allowed_actions: list[str] = []
    if stage.status == StageStatus.ACTIVE and application.rule_id is not None:
        rule_row = await db.get(WorkflowRule, application.rule_id)
        if rule_row is not None:
            rule = validate_rule_definition(rule_row.definition)
            allowed_actions = rule.stage(stage.stage_key).actions

    deadline_out = None
    if stage.deadline_id is not None:
        deadline = await db.get(Deadline, stage.deadline_id)
        if deadline is not None:
            deadline_out = DeadlineOut(
                id=str(deadline.id),
                due_at=deadline.due_at,
                status=deadline.status,
                owner_party=deadline.owner_party.value,
            )

    return StageInstanceOut(
        id=str(stage.id),
        application_id=str(application.id),
        app_no=application.app_no,
        institution_name=institution.name,
        stage_key=stage.stage_key,
        seq=stage.seq,
        status=stage.status,
        activated_at=stage.activated_at,
        completed_at=stage.completed_at,
        returns_count=stage.returns_count,
        assigned_user_id=str(stage.assigned_user_id) if stage.assigned_user_id else None,
        deadline=deadline_out,
        allowed_actions=allowed_actions,
    )
