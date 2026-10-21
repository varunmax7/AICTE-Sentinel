"""Phase P2 slice of the seed script (IMPLEMENTATION.md §18.2, Phase P2 task
list: "Seed: application types, rules, deficiency reasons, a handful of
applications"). Called from `app.seed.seed.seed()` after the P1 region/
institution/user rows exist.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.db.models.deadline import Holiday
from app.db.models.enums import ApplicationStatus, ApplicationType, UserRole, WorkflowRuleStatus
from app.db.models.institution import Institution
from app.db.models.user import User
from app.db.models.workflow import (
    Application,
    ApplicationTypeDef,
    DeficiencyReason,
    StageInstance,
    WorkflowRule,
)
from app.services.workflow.engine import perform_action, route
from app.services.workflow.rules import validate_rule_definition

ACADEMIC_YEAR = "2026-27"

_SCRUTINY_STAGE = {
    "key": "SCRUTINY",
    "label_key": "stage.scrutiny",
    "kind": "HUMAN",
    "role": "SCRUTINY_OFFICER",
    "sla_days": 15,
    "sla_calendar": "WORKING_DAYS",
    "actions": ["CLEAR", "RETURN", "REFER_SENIOR", "REQUEST_CLARIFICATION"],
    "pause_clock_on": ["RETURN", "REQUEST_CLARIFICATION"],
    "max_returns": 2,
    "auto_advance_on_clear": True,
    "escalation_policy": "STAGE_DEFAULT",
}
_EVC_STAGE = {
    "key": "EVC",
    "label_key": "stage.evc",
    "kind": "HUMAN",
    "role": "REGIONAL_OFFICER",
    "sla_days": 30,
    "sla_calendar": "CALENDAR_DAYS",
    "sub_steps": ["QUEUED", "PANEL_PROPOSED", "SCHEDULED", "VISITED", "REPORT_SUBMITTED"],
    "actions": ["SCHEDULE", "RESCHEDULE", "COMPLETE"],
    "auto_advance_on_clear": True,
    "escalation_policy": "EVC_DEFAULT",
}
_SAC_STAGE = {
    "key": "SAC",
    "label_key": "stage.sac",
    "kind": "HUMAN",
    "role": "COMMITTEE_MEMBER",
    "sla_days": 10,
    "actions": ["DECIDE"],
    "decisions": ["APPROVE", "APPROVE_WITH_CONDITIONS", "REJECT", "DEFER"],
    "requires_otp": True,
    "escalation_policy": "STAGE_DEFAULT",
}
_PRECHECK_STAGE = {
    "key": "AI_PRECHECK",
    "label_key": "stage.ai_precheck",
    "kind": "SYSTEM",
    "sla_days": 0,
    "auto_complete": True,
}

# §9.1 pathway table: application type -> stage list + required document
# types. The doc codes match `document_types.code` (Phase P3's
# `app.services.docai.schemas`) now that table exists — P2 seeded this
# phase's own placeholder codes before Document AI landed; this is the
# "required_document_types" these checks actually resolve against, used by
# `app.services.docai.pipeline.run_application_checks`'s
# INFRASTRUCTURE_VERIFICATION check.
_PATHWAYS: dict[ApplicationType, tuple[list[dict[str, object]], list[str]]] = {
    ApplicationType.EXTENSION_OF_APPROVAL: (
        [_PRECHECK_STAGE, _SCRUTINY_STAGE],
        ["AFFIDAVIT"],
    ),
    ApplicationType.CHANGE_OF_NAME: (
        [_PRECHECK_STAGE, _SCRUTINY_STAGE],
        ["AFFIDAVIT"],
    ),
    ApplicationType.INTAKE_INCREASE: (
        [_PRECHECK_STAGE, _SCRUTINY_STAGE, _EVC_STAGE],
        ["FACULTY_LIST", "BUILDING_PLAN_APPROVAL"],
    ),
    ApplicationType.NEW_COURSE: (
        [_PRECHECK_STAGE, _SCRUTINY_STAGE, _EVC_STAGE],
        ["FACULTY_LIST", "BUILDING_PLAN_APPROVAL"],
    ),
    ApplicationType.CHANGE_OF_SITE: (
        [_PRECHECK_STAGE, _EVC_STAGE, _SAC_STAGE],
        ["LEASE_DEED", "BUILDING_PLAN_APPROVAL"],
    ),
    ApplicationType.COLLABORATION: (
        [_PRECHECK_STAGE, _EVC_STAGE],
        ["AFFIDAVIT"],
    ),
    ApplicationType.NEW_INSTITUTION: (
        [_PRECHECK_STAGE, _SCRUTINY_STAGE, _EVC_STAGE, _SAC_STAGE],
        ["LEASE_DEED", "FIRE_NOC", "BUILDING_PLAN_APPROVAL"],
    ),
}

_DEFICIENCY_REASONS = [
    ("MISSING_DOCUMENT", "deficiency.missingDocument", "DOCUMENT"),
    ("FIRE_NOC_EXPIRED", "deficiency.fireNocExpired", "DOCUMENT"),
    ("LAND_AREA_SHORTFALL", "deficiency.landAreaShortfall", "COMPLIANCE"),
    ("INVALID_SIGNATURE", "deficiency.invalidSignature", "DOCUMENT"),
    ("INCOMPLETE_FACULTY_DATA", "deficiency.incompleteFacultyData", "COMPLIANCE"),
    ("OTHER", "deficiency.other", "OTHER"),
]

_HOLIDAYS = [
    (date(2026, 8, 15), "Independence Day"),
    (date(2026, 10, 2), "Gandhi Jayanti"),
    (date(2027, 1, 26), "Republic Day"),
]


async def _seed_rule_and_type(
    db: AsyncSession,
    *,
    application_type: ApplicationType,
    stages: list[dict[str, object]],
    docs: list[str],
) -> None:
    rule_key = f"{application_type.value}@{ACADEMIC_YEAR}@v1"
    existing_rule = await db.execute(select(WorkflowRule).where(WorkflowRule.rule_key == rule_key))
    rule = existing_rule.scalar_one_or_none()
    if rule is None:
        definition = {
            "rule_id": rule_key,
            "application_type": application_type.value,
            "academic_year": ACADEMIC_YEAR,
            "version": 1,
            "stages": stages,
            "branches": [],
        }
        if application_type == ApplicationType.NEW_INSTITUTION:
            # Illustrative, inert branch (skip=False never changes routing) —
            # exercises the validator + evaluator end to end, see §9.2.
            definition["branches"] = [
                {
                    "when": "application.payload.is_government == True and stage == 'SAC'",
                    "skip": False,
                }
            ]
        validate_rule_definition(definition)  # raises if the seed data is malformed
        rule = WorkflowRule(
            rule_key=rule_key,
            application_type=application_type,
            academic_year=ACADEMIC_YEAR,
            version=1,
            definition=definition,
            status=WorkflowRuleStatus.PUBLISHED,
        )
        db.add(rule)
        await db.flush()

    existing_type = await db.execute(
        select(ApplicationTypeDef).where(ApplicationTypeDef.code == application_type)
    )
    type_row = existing_type.scalar_one_or_none()
    if type_row is None:
        db.add(
            ApplicationTypeDef(
                code=application_type,
                name_key=f"applicationType.{application_type.value}",
                required_document_types=docs,
                default_rule_id=rule.id,
            )
        )


async def _seed_deficiency_reasons(db: AsyncSession) -> None:
    for code, label_key, category in _DEFICIENCY_REASONS:
        existing = await db.execute(select(DeficiencyReason).where(DeficiencyReason.code == code))
        if existing.scalar_one_or_none() is None:
            db.add(DeficiencyReason(code=code, label_key=label_key, category=category))


async def _seed_holidays(db: AsyncSession) -> None:
    for holiday_date, name in _HOLIDAYS:
        existing = await db.execute(select(Holiday).where(Holiday.date == holiday_date))
        if existing.scalar_one_or_none() is None:
            db.add(Holiday(date=holiday_date, name=name, region_id=None))


async def _submit_and_route(
    db: AsyncSession,
    *,
    institution: Institution,
    application_type: ApplicationType,
    app_no: str,
    payload: dict[str, object],
) -> Application:
    rule_result = await db.execute(
        select(WorkflowRule).where(
            WorkflowRule.application_type == application_type,
            WorkflowRule.academic_year == ACADEMIC_YEAR,
            WorkflowRule.status == WorkflowRuleStatus.PUBLISHED,
        )
    )
    rule = rule_result.scalar_one()

    application = Application(
        institution_id=institution.id,
        application_type=application_type,
        academic_year=ACADEMIC_YEAR,
        payload=payload,
        rule_id=rule.id,
        app_no=app_no,
        status=ApplicationStatus.SUBMITTED,
        submitted_at=clock.now(),
    )
    db.add(application)
    await db.commit()
    await route(db, application)
    return application


async def seed_workflow(
    db: AsyncSession, *, institution: Institution, users_by_role: dict[UserRole, User]
) -> None:
    for application_type, (stages, docs) in _PATHWAYS.items():
        await _seed_rule_and_type(db, application_type=application_type, stages=stages, docs=docs)
    await _seed_deficiency_reasons(db)
    await _seed_holidays(db)
    await db.commit()

    existing_apps = await db.execute(
        select(Application).where(Application.institution_id == institution.id)
    )
    if existing_apps.first() is not None:
        return  # already seeded on a previous run

    db.add(
        Application(
            institution_id=institution.id,
            application_type=ApplicationType.EXTENSION_OF_APPROVAL,
            academic_year=ACADEMIC_YEAR,
            payload={"notes": "Draft — not yet submitted."},
        )
    )
    await db.commit()

    await _submit_and_route(
        db,
        institution=institution,
        application_type=ApplicationType.NEW_INSTITUTION,
        app_no="APP-2026-0001",
        payload={"is_government": True},
    )
    in_evc = await _submit_and_route(
        db,
        institution=institution,
        application_type=ApplicationType.INTAKE_INCREASE,
        app_no="APP-2026-0002",
        payload={},
    )

    scrutiny_officer = users_by_role.get(UserRole.SCRUTINY_OFFICER)
    if scrutiny_officer is not None:
        stage_result = await db.execute(
            select(StageInstance).where(
                StageInstance.application_id == in_evc.id, StageInstance.stage_key == "SCRUTINY"
            )
        )
        scrutiny_stage = stage_result.scalar_one_or_none()
        if scrutiny_stage is not None:
            await perform_action(db, scrutiny_stage, action="CLEAR", actor=scrutiny_officer)

    print("Workflow seed complete: 3 demo applications (1 draft, 1 at SCRUTINY, 1 at EVC).")
