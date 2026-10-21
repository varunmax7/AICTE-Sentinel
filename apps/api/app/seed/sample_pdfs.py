"""Generates the sample PDFs the Phase P3 seed attaches to the hero case
(IMPLEMENTATION.md §18.2, Phase P3 task list: "Hero case seed with
generated sample PDFs"). Text is laid out to match the regex patterns in
`app.services.docai.schemas`, same as a real extractor's patterns would be
tuned to its own document templates — see that module's docstring.
"""

from __future__ import annotations

import io

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _render_lines(title: str, lines: list[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 800, title)
    c.setFont("Helvetica", 11)
    y = 760
    for line in lines:
        c.drawString(72, y, line)
        y -= 20
    c.showPage()
    c.save()
    return buf.getvalue()


def lease_deed_pdf(
    *,
    lessor: str,
    lessee: str,
    survey_no: str,
    land_area_acres: float,
    start_date: str,
    expiry_date: str,
    registration_no: str,
    stamp_duty_amount: int,
) -> bytes:
    return _render_lines(
        "LEASE DEED",
        [
            f"Lessor: {lessor}",
            f"Lessee: {lessee}",
            f"Survey No: {survey_no}",
            f"Land Area: {land_area_acres} acres",
            f"Lease Start Date: {start_date}",
            f"Lease Expiry Date: {expiry_date}",
            f"Registration No: {registration_no}",
            f"Stamp Duty: Rs {stamp_duty_amount}",
        ],
    )


def fire_noc_pdf(*, issuing_authority: str, issued_date: str, expiry_date: str) -> bytes:
    return _render_lines(
        "FIRE SAFETY NO-OBJECTION CERTIFICATE",
        [
            f"Issuing Authority: {issuing_authority}",
            f"Issued Date: {issued_date}",
            f"Expiry Date: {expiry_date}",
        ],
    )


def building_plan_approval_pdf(
    *, approval_no: str, approved_date: str, built_up_area_sqft: int
) -> bytes:
    return _render_lines(
        "BUILDING PLAN APPROVAL",
        [
            f"Approval No: {approval_no}",
            f"Approved Date: {approved_date}",
            f"Built-Up Area: {built_up_area_sqft} sq ft",
        ],
    )
