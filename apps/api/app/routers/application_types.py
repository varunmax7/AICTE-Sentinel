"""`GET /application-types` (IMPLEMENTATION.md §13.2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models.user import User
from app.db.models.workflow import ApplicationTypeDef
from app.db.session import get_db
from app.schemas.workflow import ApplicationTypeOut

router = APIRouter(tags=["application-types"])


@router.get("/application-types", response_model=list[ApplicationTypeOut])
async def list_application_types(
    _user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ApplicationTypeOut]:
    result = await db.execute(select(ApplicationTypeDef).order_by(ApplicationTypeDef.code))
    return [
        ApplicationTypeOut(
            code=t.code, name_key=t.name_key, required_document_types=t.required_document_types
        )
        for t in result.scalars()
    ]
