"""`GET/PATCH /me` (IMPLEMENTATION.md §13.1) — profile, language, theme."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models.enums import ActorType
from app.db.models.user import User
from app.db.session import get_db
from app.routers.auth import build_me
from app.schemas.auth import MeOut, MeUpdateRequest
from app.services.audit.chain import write_audit_event

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeOut)
async def get_me(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MeOut:
    return await build_me(db, user)


@router.patch("/me", response_model=MeOut)
async def update_me(
    body: MeUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeOut:
    before = {
        "name": user.name,
        "preferred_language": user.preferred_language,
        "theme": user.theme.value,
    }

    if body.name is not None:
        user.name = body.name
    if body.preferred_language is not None:
        user.preferred_language = body.preferred_language
    if body.theme is not None:
        user.theme = body.theme

    after = {
        "name": user.name,
        "preferred_language": user.preferred_language,
        "theme": user.theme.value,
    }

    await write_audit_event(
        db,
        actor_type=ActorType.USER,
        actor_id=str(user.id),
        action="user.profile_updated",
        entity_type="user",
        entity_id=user.id,
        before=before,
        after=after,
    )
    await db.commit()

    return await build_me(db, user)
