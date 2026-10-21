"""Per-document-type extraction schemas (IMPLEMENTATION.md §14: "vision LLM
with per-type JSON schema"). Each field maps to a regex run against the
OCR'd raw text — see `app.services.docai.extract`. These are the field
lists stored on `document_types.extraction_schema`, seeded in
`app.seed.docai_seed`.
"""

from __future__ import annotations

import re

LEASE_DEED = "LEASE_DEED"
BUILDING_PLAN_APPROVAL = "BUILDING_PLAN_APPROVAL"
FIRE_NOC = "FIRE_NOC"
AFFIDAVIT = "AFFIDAVIT"
FACULTY_LIST = "FACULTY_LIST"

EXTRACTION_SCHEMAS: dict[str, list[str]] = {
    LEASE_DEED: [
        "lessor",
        "lessee",
        "survey_no",
        "land_area_acres",
        "start_date",
        "expiry_date",
        "registration_no",
        "stamp_duty_amount",
    ],
    BUILDING_PLAN_APPROVAL: ["approval_no", "approved_date", "built_up_area_sqft"],
    FIRE_NOC: ["issuing_authority", "issued_date", "expiry_date"],
    AFFIDAVIT: ["affiant_name", "affidavit_date"],
    FACULTY_LIST: ["faculty_count"],
}

# One capturing group each — matched case-insensitively against the raw OCR
# text. Written to match the layout `app.seed.docai_seed`'s generated sample
# PDFs use, same as a real extractor would be tuned to its document templates.
_FIELD_PATTERNS: dict[str, dict[str, re.Pattern[str]]] = {
    LEASE_DEED: {
        "lessor": re.compile(r"Lessor\s*:\s*([A-Za-z0-9 .,&'-]+?)(?=\s{2,}|\n|Lessee|$)", re.I),
        "lessee": re.compile(r"Lessee\s*:\s*([A-Za-z0-9 .,&'-]+?)(?=\s{2,}|\n|Survey|$)", re.I),
        "survey_no": re.compile(r"Survey\s*No\.?\s*:\s*([A-Za-z0-9/-]+)", re.I),
        "land_area_acres": re.compile(r"Land\s*Area\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*acres?", re.I),
        "start_date": re.compile(
            r"Lease\s*Start\s*Date\s*:\s*([0-9]{1,2}[-/][A-Za-z0-9]+[-/][0-9]{2,4})", re.I
        ),
        "expiry_date": re.compile(
            r"Lease\s*Expiry\s*Date\s*:\s*([0-9]{1,2}[-/][A-Za-z0-9]+[-/][0-9]{2,4})", re.I
        ),
        "registration_no": re.compile(r"Registration\s*No\.?\s*:\s*([A-Za-z0-9/-]+)", re.I),
        "stamp_duty_amount": re.compile(r"Stamp\s*Duty\s*:\s*(?:Rs\.?|INR)?\s*([0-9,]+)", re.I),
    },
    BUILDING_PLAN_APPROVAL: {
        "approval_no": re.compile(r"Approval\s*No\.?\s*:\s*([A-Za-z0-9/-]+)", re.I),
        "approved_date": re.compile(
            r"Approved\s*Date\s*:\s*([0-9]{1,2}[-/][A-Za-z0-9]+[-/][0-9]{2,4})", re.I
        ),
        "built_up_area_sqft": re.compile(r"Built[- ]?Up\s*Area\s*:\s*([0-9,]+)\s*sq", re.I),
    },
    FIRE_NOC: {
        "issuing_authority": re.compile(r"Issuing\s*Authority\s*:\s*([A-Za-z0-9 .,&'-]+)", re.I),
        "issued_date": re.compile(
            r"Issued\s*Date\s*:\s*([0-9]{1,2}[-/][A-Za-z0-9]+[-/][0-9]{2,4})", re.I
        ),
        "expiry_date": re.compile(
            r"Expiry\s*Date\s*:\s*([0-9]{1,2}[-/][A-Za-z0-9]+[-/][0-9]{2,4})", re.I
        ),
    },
    AFFIDAVIT: {
        "affiant_name": re.compile(r"Affiant\s*:\s*([A-Za-z0-9 .,&'-]+)", re.I),
        "affidavit_date": re.compile(
            r"Date\s*:\s*([0-9]{1,2}[-/][A-Za-z0-9]+[-/][0-9]{2,4})", re.I
        ),
    },
    FACULTY_LIST: {
        "faculty_count": re.compile(r"Total\s*Faculty\s*:\s*([0-9]+)", re.I),
    },
}


def field_patterns(document_type: str) -> dict[str, re.Pattern[str]]:
    return _FIELD_PATTERNS.get(document_type, {})
