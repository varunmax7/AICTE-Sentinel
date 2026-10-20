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
