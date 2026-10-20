"""Deficiency-letter drafting (IMPLEMENTATION.md §9.6, §13.3).

Phase P2 ships the RETURN/deficiency-letter plumbing (draft → officer edits
→ send) with a deterministic Markdown template standing in for the AI draft
— real LLM drafting is Phase P3+ scope per the Phase P2 task list ("letter
draft can return a template stub until AI lands").
"""

from __future__ import annotations


def render_deficiency_letter_stub(
    *,
    institution_name: str,
    app_no: str | None,
    reason: str,
    deficiencies: list[str],
) -> str:
    bullet_list = "\n".join(f"- {d}" for d in deficiencies) or "- (see reason below)"
    reference = app_no or "your application"
    return (
        f"Dear {institution_name},\n\n"
        f"Your application {reference} has been returned for the following "
        f"deficiencies:\n\n"
        f"{bullet_list}\n\n"
        f"Reason: {reason}\n\n"
        f"Please resubmit with the required corrections at the earliest. "
        f"The processing clock for this stage is paused until you respond.\n\n"
        f"Regards,\nAICTE Approval & Compliance Portal"
    )
