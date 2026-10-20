from pydantic import BaseModel, Field

from app.db.models.enums import ThemePref, UserRole


class OtpSendRequest(BaseModel):
    identifier: str = Field(..., description="Phone number in E.164 form, e.g. +91XXXXXXXXXX")
    role: UserRole


class OtpSendResponse(BaseModel):
    sent: bool
    expires_in_seconds: int


class OtpVerifyRequest(BaseModel):
    identifier: str
    role: UserRole
    code: str


class RegionOut(BaseModel):
    id: str
    code: str
    name: str


class MeOut(BaseModel):
    id: str
    name: str
    role: UserRole
    preferred_language: str
    theme: ThemePref
    institution_id: str | None
    regions: list[RegionOut]


class MeUpdateRequest(BaseModel):
    preferred_language: str | None = None
    theme: ThemePref | None = None
    name: str | None = None
