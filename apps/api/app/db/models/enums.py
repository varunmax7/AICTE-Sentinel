import enum


class UserRole(enum.StrEnum):
    """IMPLEMENTATION.md §2.1."""

    INSTITUTION = "INSTITUTION"
    SCRUTINY_OFFICER = "SCRUTINY_OFFICER"
    REGIONAL_OFFICER = "REGIONAL_OFFICER"
    BUREAU_HEAD = "BUREAU_HEAD"
    COMMITTEE_MEMBER = "COMMITTEE_MEMBER"
    EVC_EXPERT = "EVC_EXPERT"
    ADMIN = "ADMIN"
    PUBLIC = "PUBLIC"
    FACULTY = "FACULTY"


# Roles scoped to the authority's full region set (not filtered to user_regions).
UNSCOPED_ROLES = {UserRole.BUREAU_HEAD, UserRole.ADMIN}


class InstitutionType(enum.StrEnum):
    GOVT = "GOVT"
    PRIVATE = "PRIVATE"
    AIDED = "AIDED"
    DEEMED = "DEEMED"


class ThemePref(enum.StrEnum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class OtpPurpose(enum.StrEnum):
    LOGIN = "LOGIN"
    ESIGN = "ESIGN"


class OtpStatus(enum.StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class ActorType(enum.StrEnum):
    """IMPLEMENTATION.md §16."""

    USER = "USER"
    SYSTEM = "SYSTEM"
    VOICE = "VOICE"
    AI = "AI"


class ApplicationType(enum.StrEnum):
    """Seed application types (IMPLEMENTATION.md §9.1). More are added via the
    admin workflow-rule builder in P10 without needing a new enum member —
    this enum only needs to cover the Phase P2 seed pathways.
    """

    NEW_INSTITUTION = "NEW_INSTITUTION"
    EXTENSION_OF_APPROVAL = "EXTENSION_OF_APPROVAL"
    INTAKE_INCREASE = "INTAKE_INCREASE"
    NEW_COURSE = "NEW_COURSE"
    CHANGE_OF_NAME = "CHANGE_OF_NAME"
    CHANGE_OF_SITE = "CHANGE_OF_SITE"
    COLLABORATION = "COLLABORATION"
    CLOSURE = "CLOSURE"


class WorkflowRuleStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    RETIRED = "RETIRED"


class ApplicationStatus(enum.StrEnum):
    """§9.3 `Application.status` state machine."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    IN_PROCESS = "IN_PROCESS"
    DECISION_RECORDED = "DECISION_RECORDED"
    APPROVED = "APPROVED"
    APPROVED_WITH_CONDITIONS = "APPROVED_WITH_CONDITIONS"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class StageStatus(enum.StrEnum):
    """§9.3 `StageInstance.status` state machine."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    RETURNED = "RETURNED"
    REFERRED = "REFERRED"
    SKIPPED = "SKIPPED"


class StageAction(enum.StrEnum):
    """Actions an officer can take on an active stage (§9.4, §13.3)."""

    CLEAR = "CLEAR"
    RETURN = "RETURN"
    REFER_SENIOR = "REFER_SENIOR"
    REQUEST_CLARIFICATION = "REQUEST_CLARIFICATION"
    SCHEDULE = "SCHEDULE"
    RESCHEDULE = "RESCHEDULE"
    COMPLETE = "COMPLETE"
    DECIDE = "DECIDE"


class DeficiencyStatus(enum.StrEnum):
    OPEN = "OPEN"
    RESPONDED = "RESPONDED"
    RESOLVED = "RESOLVED"


class DeadlineStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class DeadlineOwnerParty(enum.StrEnum):
    """Which side currently "owns" the clock on a deadline — the officer
    working the stage, or the institution while a deficiency response is
    pending (§9.6). Drives whose SLA the deadline counts against.
    """

    OFFICER = "OFFICER"
    INSTITUTION = "INSTITUTION"


class DocumentSource(enum.StrEnum):
    """IMPLEMENTATION.md §21. Only `PORTAL` is wired in Phase P3 — the other
    three channels light up alongside the matching Phase P7 inbound adapter
    (email/WhatsApp) or P6 upload-link flow.
    """

    PORTAL = "PORTAL"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    LINK = "LINK"


class DocumentVerifiedStatus(enum.StrEnum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class ExtractionStatus(enum.StrEnum):
    PENDING = "PENDING"
    DONE = "DONE"
    FAILED = "FAILED"


class AiCheckStatus(enum.StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class AiFlagSeverity(enum.StrEnum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class AiFlagStatus(enum.StrEnum):
    OPEN = "OPEN"
    DISMISSED = "DISMISSED"
    CONFIRMED = "CONFIRMED"
