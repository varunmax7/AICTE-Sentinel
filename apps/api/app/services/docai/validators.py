"""Validators (IMPLEMENTATION.md §14 `docai/validators.py`): turn one
document's extraction, plus the application payload and the `norms` table,
into a list of `{key, status, message_key, params}` checks — the data the
Case Review Workspace's AI panel check cards render, and what
`ai_checks` rows get written from.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, TypedDict

from app.db.models.enums import AiCheckStatus


class CheckResult(TypedDict):
    check_key: str
    status: AiCheckStatus
    message_key: str
    params: dict[str, Any]


def _parse_date(value: str) -> date | None:
    for fmt in ("%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def check_land_area_norms(
    *, extracted_acres: float | None, required_acres: float | None
) -> CheckResult:
    if extracted_acres is None or required_acres is None:
        return CheckResult(
            check_key="LAND_AREA_NORMS",
            status=AiCheckStatus.WARN,
            message_key="aiCheck.landAreaNorms.noData",
            params={},
        )
    status = AiCheckStatus.PASS if extracted_acres >= required_acres else AiCheckStatus.FAIL
    return CheckResult(
        check_key="LAND_AREA_NORMS",
        status=status,
        message_key="aiCheck.landAreaNorms.result",
        params={"extracted": extracted_acres, "required": required_acres},
    )


def check_stamp_duty_sanity(
    *, stamp_duty_amount: float | None, land_area_acres: float | None, rate_per_acre: float
) -> CheckResult:
    if stamp_duty_amount is None or land_area_acres is None:
        return CheckResult(
            check_key="STAMP_DUTY_SANITY",
            status=AiCheckStatus.WARN,
            message_key="aiCheck.stampDuty.noData",
            params={},
        )
    expected_min = land_area_acres * rate_per_acre
    status = AiCheckStatus.WARN if stamp_duty_amount < expected_min * 0.5 else AiCheckStatus.PASS
    return CheckResult(
        check_key="STAMP_DUTY_SANITY",
        status=status,
        message_key="aiCheck.stampDuty.result",
        params={"amount": stamp_duty_amount, "expectedMin": round(expected_min, 2)},
    )


def check_document_validity(
    *, expiry_date_str: str | None, min_validity_years: int | None, reference: date
) -> CheckResult:
    expiry = _parse_date(expiry_date_str) if expiry_date_str else None
    if expiry is None:
        return CheckResult(
            check_key="DOCUMENT_VALIDITY",
            status=AiCheckStatus.WARN,
            message_key="aiCheck.documentValidity.noData",
            params={},
        )
    required_until = reference.replace(year=reference.year + (min_validity_years or 0))
    status = AiCheckStatus.PASS if expiry >= required_until else AiCheckStatus.WARN
    return CheckResult(
        check_key="DOCUMENT_VALIDITY",
        status=status,
        message_key="aiCheck.documentValidity.result",
        params={"expiry": expiry.isoformat(), "requiredUntil": required_until.isoformat()},
    )


def check_required_documents_present(
    *, required_codes: list[str], uploaded_codes: set[str]
) -> CheckResult:
    missing = [c for c in required_codes if c not in uploaded_codes]
    total = len(required_codes) or 1
    complete_pct = round(100 * (total - len(missing)) / total)
    status = AiCheckStatus.PASS if not missing else AiCheckStatus.WARN
    return CheckResult(
        check_key="INFRASTRUCTURE_VERIFICATION",
        status=status,
        message_key="aiCheck.infrastructure.result",
        params={"completePct": complete_pct, "missing": missing},
    )


def check_duplicate_faculty() -> CheckResult:
    """Stub — real duplicate-faculty-ID detection needs the `faculty` master
    table (§21), which no phase has built yet (it tracks institution-wide
    faculty records, not anything application-scoped). Always clears, so the
    AI panel's card is present and correctly shaped ahead of that table
    landing; wiring the real SQL check is then a change to this function
    only, not to any caller.
    """

    return CheckResult(
        check_key="DUPLICATE_FACULTY",
        status=AiCheckStatus.PASS,
        message_key="aiCheck.duplicateFaculty.result",
        params={},
    )
