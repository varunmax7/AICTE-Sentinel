"""Workflow engine tests (IMPLEMENTATION.md §19 Phase P2 acceptance): every
PS pathway routes correctly, CLEAR auto-advances, RETURN pauses the SLA and
creates a deficiency letter, resubmit resumes and re-scrutinizes, the
max-returns warning is recorded without blocking, and role/region/assignment
permission checks reject the actor they should.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.security import encrypt_field, hash_identifier
from app.db.models.deadline import Deadline
from app.db.models.enums import (
    ApplicationStatus,
    ApplicationType,
    DeadlineStatus,
    DeficiencyStatus,
    InstitutionType,
    StageStatus,
    UserRole,
    WorkflowRuleStatus,
)
from app.db.models.geo import Region, State
from app.db.models.institution import Institution
from app.db.models.user import User, UserRegion
from app.db.models.workflow import (
    Application,
    Deficiency,
    DeficiencyLetter,
    StageInstance,
    StageTransition,
    WorkflowRule,
)
from app.db.session import SessionLocal
from app.services.workflow.engine import WorkflowError, perform_action, resubmit, route

_phone_counter = 0


def _next_phone() -> str:
    global _phone_counter
    _phone_counter += 1
    return f"+9199900{_phone_counter:05d}"


async def _make_region(db, code: str = "HYD") -> Region:
    region = Region(
        code=f"{code}-{uuid.uuid4().hex[:6]}", name=f"{code} Region", office_city="City"
    )
    db.add(region)
    await db.flush()
    return region


async def _make_institution(db, region: Region) -> Institution:
    state = State(code=f"ST-{uuid.uuid4().hex[:6]}", name="State", region_id=region.id)
    db.add(state)
    await db.flush()
    inst = Institution(
        aicte_id=f"AICTE-{uuid.uuid4().hex[:8]}",
        name="Test College",
        type=InstitutionType.GOVT,
        state_id=state.id,
        region_id=region.id,
        city="City",
        address="Addr",
    )
    db.add(inst)
    await db.flush()
    return inst


async def _make_user(db, *, role: UserRole, region: Region | None) -> User:
    phone = _next_phone()
    user = User(
        role=role,
        name=f"{role.value} {phone}",
        phone_enc=encrypt_field(phone),
        phone_hash=hash_identifier(phone),
    )
    db.add(user)
    await db.flush()
    if region is not None:
        db.add(UserRegion(user_id=user.id, region_id=region.id))
        await db.flush()
    return user


_STAGES: dict[str, dict[str, object]] = {
    "PRECHECK": {
        "key": "AI_PRECHECK",
        "label_key": "x",
        "kind": "SYSTEM",
        "sla_days": 0,
        "auto_complete": True,
    },
    "SCRUTINY": {
        "key": "SCRUTINY",
        "label_key": "x",
        "kind": "HUMAN",
        "role": "SCRUTINY_OFFICER",
        "sla_days": 15,
        "sla_calendar": "WORKING_DAYS",
        "actions": ["CLEAR", "RETURN", "REFER_SENIOR", "REQUEST_CLARIFICATION"],
        "pause_clock_on": ["RETURN", "REQUEST_CLARIFICATION"],
        "max_returns": 2,
        "auto_advance_on_clear": True,
    },
    "EVC": {
        "key": "EVC",
        "label_key": "x",
        "kind": "HUMAN",
        "role": "REGIONAL_OFFICER",
        "sla_days": 30,
        "sla_calendar": "CALENDAR_DAYS",
        "actions": ["COMPLETE"],
        "auto_advance_on_clear": True,
    },
    "SAC": {
        "key": "SAC",
        "label_key": "x",
        "kind": "HUMAN",
        "role": "COMMITTEE_MEMBER",
        "sla_days": 10,
        "actions": ["DECIDE"],
        "decisions": ["APPROVE"],
        "requires_otp": True,
    },
}


async def _make_rule(
    db, *, application_type: ApplicationType, stage_names: list[str]
) -> WorkflowRule:
    stages = [_STAGES[name] for name in stage_names]
    rule = WorkflowRule(
        rule_key=f"{application_type.value}@test@{uuid.uuid4().hex[:8]}",
        application_type=application_type,
        academic_year="2026-27",
        version=1,
        definition={
            "rule_id": "test",
            "application_type": application_type.value,
            "academic_year": "2026-27",
            "version": 1,
            "stages": stages,
            "branches": [],
        },
        status=WorkflowRuleStatus.PUBLISHED,
    )
    db.add(rule)
    await db.flush()
    return rule


async def _make_application(
    db, *, institution: Institution, rule: WorkflowRule, payload: dict | None = None
) -> Application:
    application = Application(
        institution_id=institution.id,
        application_type=rule.application_type,
        academic_year=rule.academic_year,
        rule_id=rule.id,
        payload=payload or {},
        status=ApplicationStatus.SUBMITTED,
    )
    db.add(application)
    await db.flush()
    return application


async def _stage_instances(db, application: Application) -> list[StageInstance]:
    result = await db.execute(
        select(StageInstance)
        .where(StageInstance.application_id == application.id)
        .order_by(StageInstance.seq)
    )
    return list(result.scalars())


async def _stage_by_key(db, application: Application, key: str) -> StageInstance:
    result = await db.execute(
        select(StageInstance).where(
            StageInstance.application_id == application.id, StageInstance.stage_key == key
        )
    )
    return result.scalar_one()


# §9.1's five PS (pathway) combinations.
_PATHWAYS = [
    ["PRECHECK", "SCRUTINY"],  # Only Scrutiny
    ["PRECHECK", "SCRUTINY", "EVC"],  # Scrutiny + EVC
    ["PRECHECK", "EVC", "SAC"],  # EVC + SAC
    ["PRECHECK", "EVC"],  # Only EVC
    ["PRECHECK", "SCRUTINY", "EVC", "SAC"],  # Scrutiny + EVC + SAC
]


@pytest.mark.parametrize("stage_names", _PATHWAYS, ids=["-".join(p) for p in _PATHWAYS])
async def test_route_creates_expected_stage_sequence_for_every_pathway(
    stage_names: list[str],
) -> None:
    async with SessionLocal() as db:
        region = await _make_region(db)
        institution = await _make_institution(db, region)
        human_roles = {_STAGES[n]["role"] for n in stage_names if _STAGES[n]["kind"] == "HUMAN"}
        for role_name in human_roles:
            await _make_user(db, role=UserRole(role_name), region=region)
        rule = await _make_rule(
            db, application_type=ApplicationType.NEW_INSTITUTION, stage_names=stage_names
        )
        application = await _make_application(db, institution=institution, rule=rule)
        await db.commit()

        await route(db, application)

        stages = await _stage_instances(db, application)
        assert [s.stage_key for s in stages] == [_STAGES[n]["key"] for n in stage_names]
        assert stages[0].status == StageStatus.COMPLETED  # AI_PRECHECK auto-completes
        assert stages[1].status == StageStatus.ACTIVE  # first HUMAN stage activates
        assert stages[1].assigned_user_id is not None  # auto-assigned (§9.5)

        await db.refresh(application)
        assert application.status == ApplicationStatus.IN_PROCESS
        assert application.current_stage_key == stages[1].stage_key


async def test_clear_action_auto_advances_to_next_stage() -> None:
    async with SessionLocal() as db:
        region = await _make_region(db)
        institution = await _make_institution(db, region)
        scrutiny_officer = await _make_user(db, role=UserRole.SCRUTINY_OFFICER, region=region)
        regional_officer = await _make_user(db, role=UserRole.REGIONAL_OFFICER, region=region)
        rule = await _make_rule(
            db,
            application_type=ApplicationType.INTAKE_INCREASE,
            stage_names=["PRECHECK", "SCRUTINY", "EVC"],
        )
        application = await _make_application(db, institution=institution, rule=rule)
        await db.commit()
        await route(db, application)

        scrutiny_stage = await _stage_by_key(db, application, "SCRUTINY")
        assert scrutiny_stage.assigned_user_id == scrutiny_officer.id

        updated = await perform_action(db, scrutiny_stage, action="CLEAR", actor=scrutiny_officer)
        assert updated.status == StageStatus.COMPLETED

        evc_stage = await _stage_by_key(db, application, "EVC")
        assert evc_stage.status == StageStatus.ACTIVE
        assert evc_stage.assigned_user_id == regional_officer.id

        await db.refresh(application)
        assert application.current_stage_key == "EVC"


async def test_return_action_pauses_deadline_creates_deficiency_and_letter() -> None:
    async with SessionLocal() as db:
        region = await _make_region(db)
        institution = await _make_institution(db, region)
        officer = await _make_user(db, role=UserRole.SCRUTINY_OFFICER, region=region)
        rule = await _make_rule(
            db,
            application_type=ApplicationType.EXTENSION_OF_APPROVAL,
            stage_names=["PRECHECK", "SCRUTINY"],
        )
        application = await _make_application(db, institution=institution, rule=rule)
        await db.commit()
        await route(db, application)

        stage = await _stage_by_key(db, application, "SCRUTINY")
        deadline_id = stage.deadline_id
        assert deadline_id is not None

        updated = await perform_action(
            db,
            stage,
            action="RETURN",
            actor=officer,
            reason="Missing Fire NOC",
            deficiencies=[{"reason_code": None, "custom_text": "Fire NOC missing"}],
        )
        assert updated.status == StageStatus.RETURNED
        assert updated.returns_count == 1

        deadline = await db.get(Deadline, deadline_id)
        assert deadline is not None
        assert deadline.status == DeadlineStatus.PAUSED

        deficiencies = (
            (await db.execute(select(Deficiency).where(Deficiency.stage_instance_id == stage.id)))
            .scalars()
            .all()
        )
        assert len(deficiencies) == 1
        assert deficiencies[0].status == DeficiencyStatus.OPEN
        assert deficiencies[0].custom_text == "Fire NOC missing"

        letters = (
            (
                await db.execute(
                    select(DeficiencyLetter).where(DeficiencyLetter.stage_instance_id == stage.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(letters) == 1
        assert "Fire NOC missing" in letters[0].body_md
        assert letters[0].ai_generated is True


async def test_resubmit_resumes_stage_and_marks_deficiency_responded() -> None:
    async with SessionLocal() as db:
        region = await _make_region(db)
        institution = await _make_institution(db, region)
        officer = await _make_user(db, role=UserRole.SCRUTINY_OFFICER, region=region)
        institution_user = await _make_user(db, role=UserRole.INSTITUTION, region=None)
        rule = await _make_rule(
            db,
            application_type=ApplicationType.EXTENSION_OF_APPROVAL,
            stage_names=["PRECHECK", "SCRUTINY"],
        )
        application = await _make_application(db, institution=institution, rule=rule)
        await db.commit()
        await route(db, application)

        stage = await _stage_by_key(db, application, "SCRUTINY")
        deadline_id = stage.deadline_id
        await perform_action(
            db,
            stage,
            action="RETURN",
            actor=officer,
            reason="Missing Fire NOC",
            deficiencies=[{"custom_text": "Fire NOC missing"}],
        )
        deficiency = (
            await db.execute(select(Deficiency).where(Deficiency.stage_instance_id == stage.id))
        ).scalar_one()

        resumed = await resubmit(
            db,
            application,
            actor=institution_user,
            responses=[
                {"deficiency_id": str(deficiency.id), "response_text": "Uploaded renewed Fire NOC"}
            ],
        )
        assert resumed.status == StageStatus.ACTIVE
        assert resumed.id == stage.id

        deadline = await db.get(Deadline, deadline_id)
        assert deadline is not None
        assert deadline.status == DeadlineStatus.ACTIVE

        refreshed_deficiency = await db.get(Deficiency, deficiency.id)
        assert refreshed_deficiency is not None
        assert refreshed_deficiency.status == DeficiencyStatus.RESPONDED
        assert refreshed_deficiency.response_text == "Uploaded renewed Fire NOC"


async def test_return_records_max_returns_exceeded_without_blocking() -> None:
    async with SessionLocal() as db:
        region = await _make_region(db)
        institution = await _make_institution(db, region)
        officer = await _make_user(db, role=UserRole.SCRUTINY_OFFICER, region=region)
        institution_user = await _make_user(db, role=UserRole.INSTITUTION, region=None)
        rule = await _make_rule(
            db,
            application_type=ApplicationType.EXTENSION_OF_APPROVAL,
            stage_names=["PRECHECK", "SCRUTINY"],
        )
        application = await _make_application(db, institution=institution, rule=rule)
        await db.commit()
        await route(db, application)
        stage = await _stage_by_key(db, application, "SCRUTINY")

        # max_returns is 2 for SCRUTINY — return + resubmit twice should NOT warn yet.
        for _ in range(2):
            await perform_action(
                db,
                stage,
                action="RETURN",
                actor=officer,
                reason="r",
                deficiencies=[{"custom_text": "d"}],
            )
            deficiency = (
                (
                    await db.execute(
                        select(Deficiency).where(Deficiency.stage_instance_id == stage.id)
                    )
                )
                .scalars()
                .all()[-1]
            )
            await resubmit(
                db,
                application,
                actor=institution_user,
                responses=[{"deficiency_id": str(deficiency.id), "response_text": "fixed"}],
            )

        # the third RETURN (returns_count already at 2, == max_returns) should flag the warning.
        await perform_action(
            db,
            stage,
            action="RETURN",
            actor=officer,
            reason="r3",
            deficiencies=[{"custom_text": "d3"}],
        )

        transitions = (
            (
                await db.execute(
                    select(StageTransition)
                    .where(
                        StageTransition.stage_instance_id == stage.id,
                        StageTransition.action == "RETURN",
                    )
                    .order_by(StageTransition.at)
                )
            )
            .scalars()
            .all()
        )
        assert len(transitions) == 3
        assert transitions[0].payload["max_returns_exceeded"] is False
        assert transitions[1].payload["max_returns_exceeded"] is False
        assert transitions[2].payload["max_returns_exceeded"] is True


async def test_perform_action_rejects_wrong_role() -> None:
    async with SessionLocal() as db:
        region = await _make_region(db)
        institution = await _make_institution(db, region)
        await _make_user(db, role=UserRole.SCRUTINY_OFFICER, region=region)
        wrong_role_officer = await _make_user(db, role=UserRole.REGIONAL_OFFICER, region=region)
        rule = await _make_rule(
            db,
            application_type=ApplicationType.EXTENSION_OF_APPROVAL,
            stage_names=["PRECHECK", "SCRUTINY"],
        )
        application = await _make_application(db, institution=institution, rule=rule)
        await db.commit()
        await route(db, application)
        stage = await _stage_by_key(db, application, "SCRUTINY")

        with pytest.raises(WorkflowError) as exc_info:
            await perform_action(db, stage, action="CLEAR", actor=wrong_role_officer)
        assert exc_info.value.code == "ROLE_NOT_ALLOWED"


async def test_perform_action_rejects_out_of_region_officer() -> None:
    async with SessionLocal() as db:
        region_a = await _make_region(db, code="HYD")
        region_b = await _make_region(db, code="BLR")
        institution = await _make_institution(db, region_a)
        await _make_user(db, role=UserRole.SCRUTINY_OFFICER, region=region_a)
        outside_officer = await _make_user(db, role=UserRole.SCRUTINY_OFFICER, region=region_b)
        rule = await _make_rule(
            db,
            application_type=ApplicationType.EXTENSION_OF_APPROVAL,
            stage_names=["PRECHECK", "SCRUTINY"],
        )
        application = await _make_application(db, institution=institution, rule=rule)
        await db.commit()
        await route(db, application)
        stage = await _stage_by_key(db, application, "SCRUTINY")

        with pytest.raises(WorkflowError) as exc_info:
            await perform_action(db, stage, action="CLEAR", actor=outside_officer)
        assert exc_info.value.code == "OUT_OF_REGION"


async def test_perform_action_rejects_officer_not_assigned_to_stage() -> None:
    async with SessionLocal() as db:
        region = await _make_region(db)
        institution = await _make_institution(db, region)
        officer_a = await _make_user(db, role=UserRole.SCRUTINY_OFFICER, region=region)
        officer_b = await _make_user(db, role=UserRole.SCRUTINY_OFFICER, region=region)
        rule = await _make_rule(
            db,
            application_type=ApplicationType.EXTENSION_OF_APPROVAL,
            stage_names=["PRECHECK", "SCRUTINY"],
        )
        application = await _make_application(db, institution=institution, rule=rule)
        await db.commit()
        await route(db, application)
        stage = await _stage_by_key(db, application, "SCRUTINY")

        other = officer_b if stage.assigned_user_id == officer_a.id else officer_a

        with pytest.raises(WorkflowError) as exc_info:
            await perform_action(db, stage, action="CLEAR", actor=other)
        assert exc_info.value.code == "STAGE_NOT_ASSIGNED_TO_YOU"


async def test_workload_balancer_distributes_across_officers_in_region() -> None:
    async with SessionLocal() as db:
        region = await _make_region(db)
        institution = await _make_institution(db, region)
        officer_a = await _make_user(db, role=UserRole.SCRUTINY_OFFICER, region=region)
        officer_b = await _make_user(db, role=UserRole.SCRUTINY_OFFICER, region=region)
        rule = await _make_rule(
            db,
            application_type=ApplicationType.EXTENSION_OF_APPROVAL,
            stage_names=["PRECHECK", "SCRUTINY"],
        )

        app1 = await _make_application(db, institution=institution, rule=rule)
        await db.commit()
        await route(db, app1)
        stage1 = await _stage_by_key(db, app1, "SCRUTINY")

        app2 = await _make_application(db, institution=institution, rule=rule)
        await db.commit()
        await route(db, app2)
        stage2 = await _stage_by_key(db, app2, "SCRUTINY")

        assert {stage1.assigned_user_id, stage2.assigned_user_id} == {officer_a.id, officer_b.id}
