"""Workflow rule JSON schema + validator (IMPLEMENTATION.md §9.2).

`WorkflowRule.definition` is stored as JSONB; `RuleDefinition` is the typed,
validated shape the engine actually operates on. `validate_rule_definition`
is the one entry point that turns a raw dict (from the seed script or,
later, the P10 admin rule builder) into that typed shape — or raises
`RuleValidationError` with every problem found, not just the first.

The JSON Schema document mirroring this (`packages/contracts/workflow-rule
.schema.json`) is the cross-language contract referenced by §9.2; this
module is the Python-side enforcement of the same shape plus the semantic
checks a bare JSON Schema can't express (stage keys unique, HUMAN stages
have a role, etc).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import ApplicationType, UserRole, WorkflowRuleStatus
from app.db.models.workflow import WorkflowRule

StageKind = Literal["SYSTEM", "HUMAN"]
SlaCalendar = Literal["WORKING_DAYS", "CALENDAR_DAYS"]


class StageDef(BaseModel):
    key: str
    label_key: str
    kind: StageKind
    role: UserRole | None = None
    sla_days: int = Field(ge=0)
    sla_calendar: SlaCalendar = "CALENDAR_DAYS"
    auto_complete: bool = False
    actions: list[str] = Field(default_factory=list)
    pause_clock_on: list[str] = Field(default_factory=list)
    max_returns: int | None = None
    auto_advance_on_clear: bool = False
    escalation_policy: str | None = None
    sub_steps: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    requires_otp: bool = False

    @model_validator(mode="after")
    def _human_stage_needs_role(self) -> StageDef:
        if self.kind == "HUMAN" and self.role is None:
            raise ValueError(f"stage '{self.key}' is HUMAN but has no role")
        return self


class BranchDef(BaseModel):
    when: str
    skip: bool = False


class RuleDefinition(BaseModel):
    rule_id: str
    application_type: ApplicationType
    academic_year: str
    version: int = Field(ge=1)
    stages: list[StageDef] = Field(min_length=1)
    branches: list[BranchDef] = Field(default_factory=list)

    @field_validator("stages")
    @classmethod
    def _unique_stage_keys(cls, stages: list[StageDef]) -> list[StageDef]:
        keys = [s.key for s in stages]
        if len(keys) != len(set(keys)):
            raise ValueError(f"duplicate stage keys in rule: {keys}")
        return stages

    def stage(self, key: str) -> StageDef:
        for s in self.stages:
            if s.key == key:
                return s
        raise KeyError(f"no stage '{key}' in rule {self.rule_id}")


class RuleValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_rule_definition(data: dict[str, object]) -> RuleDefinition:
    try:
        return RuleDefinition.model_validate(data)
    except ValidationError as exc:
        messages = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
        raise RuleValidationError(messages) from exc


async def resolve_published_rule(
    db: AsyncSession, *, application_type: ApplicationType, academic_year: str
) -> WorkflowRule | None:
    result = await db.execute(
        select(WorkflowRule)
        .where(
            WorkflowRule.application_type == application_type,
            WorkflowRule.academic_year == academic_year,
            WorkflowRule.status == WorkflowRuleStatus.PUBLISHED,
        )
        .order_by(WorkflowRule.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
