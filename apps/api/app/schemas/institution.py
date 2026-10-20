from __future__ import annotations

from pydantic import BaseModel

from app.db.models.enums import InstitutionType


class InstitutionOut(BaseModel):
    id: str
    aicte_id: str
    name: str
    type: InstitutionType
    city: str
    address: str
    health_score: int | None
