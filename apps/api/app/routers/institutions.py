"""`GET /institutions/{id}` (IMPLEMENTATION.md §13.2). The institution health
score is written by compliance scoring logic that lands in Phase P6 — this
endpoint only surfaces whatever is currently stored (`null` until then), it
doesn't compute it.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models.institution import Institution
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.institution import InstitutionOut
from app.services.workflow.scope import institution_in_scope

router = APIRouter(tags=["institutions"])


@router.get("/institutions/{institution_id}", response_model=InstitutionOut)
async def get_institution(
    institution_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InstitutionOut:
    institution = await db.get(Institution, institution_id)
    if institution is None or not await institution_in_scope(db, user, institution_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "INSTITUTION_NOT_FOUND"})
    return InstitutionOut(
        id=str(institution.id),
        aicte_id=institution.aicte_id,
        name=institution.name,
        type=institution.type,
        city=institution.city,
        address=institution.address,
        health_score=institution.health_score,
    )
