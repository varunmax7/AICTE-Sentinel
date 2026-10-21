"""Deficiency-letter drafting (IMPLEMENTATION.md §9.6, §13.3, §14
`ai/letters.py`). Routed through `LLMClient` as of Phase P3 — in `DEMO_MODE`
(always true in this sandbox, see `LLMClient`'s docstring) that resolves to
the deterministic Markdown template below, now also folding in whichever
`ai_checks` already exist for the application so the draft reads like it
was written with the case in front of it, not a generic form letter.
"""

from __future__ import annotations

from app.services.docai.llm_client import LLMClient


def _render_template(
    *,
    institution_name: str,
    app_no: str | None,
    reason: str,
    deficiencies: list[str],
    failed_checks: list[str],
) -> str:
    bullet_list = "\n".join(f"- {d}" for d in deficiencies) or "- (see reason below)"
    reference = app_no or "your application"
    checks_note = (
        "\n\nOur AI pre-scrutiny also flagged: " + "; ".join(failed_checks) + "."
        if failed_checks
        else ""
    )
    return (
        f"Dear {institution_name},\n\n"
        f"Your application {reference} has been returned for the following "
        f"deficiencies:\n\n"
        f"{bullet_list}\n\n"
        f"Reason: {reason}{checks_note}\n\n"
        f"Please resubmit with the required corrections at the earliest. "
        f"The processing clock for this stage is paused until you respond.\n\n"
        f"Regards,\nAICTE Approval & Compliance Portal"
    )


async def draft_deficiency_letter_body(
    *,
    institution_name: str,
    app_no: str | None,
    reason: str,
    deficiencies: list[str],
    failed_checks: list[str] | None = None,
) -> str:
    prompt = (
        f"Draft a formal deficiency-return letter for institution "
        f"'{institution_name}', application {app_no or 'N/A'}. Reason: {reason}. "
        f"Deficiencies: {', '.join(deficiencies) or 'none listed'}. "
        f"Failed AI checks: {', '.join(failed_checks or []) or 'none'}."
    )
    return await LLMClient().complete(
        prompt=prompt,
        system="You draft formal, polite AICTE deficiency-return letters.",
        demo_fallback=lambda: _render_template(
            institution_name=institution_name,
            app_no=app_no,
            reason=reason,
            deficiencies=deficiencies,
            failed_checks=failed_checks or [],
        ),
    )
