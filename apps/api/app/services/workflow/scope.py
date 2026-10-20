"""Region/institution scoping helpers shared by the applications and stages
routers (IMPLEMENTATION.md §17): an `INSTITUTION` user only ever sees their
own institution's applications; officer roles see applications whose
institution is in one of their assigned regions; `BUREAU_HEAD`/`ADMIN` are
unscoped (`user_region_ids` already returns `None` for them).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import user_region_ids
from app.db.models.enums import UserRole
from app.db.models.institution import Institution
from app.db.models.user import User


async def institution_in_scope(db: AsyncSession, user: User, institution_id: uuid.UUID) -> bool:
    if user.role == UserRole.INSTITUTION:
        return user.institution_id == institution_id

    region_ids = await user_region_ids(db, user)
    if region_ids is None:
        return True

    institution = await db.get(Institution, institution_id)
    return institution is not None and institution.region_id in region_ids


async def scoped_region_ids(db: AsyncSession, user: User) -> Sequence[uuid.UUID] | None:
    """`None` means unscoped. Only meaningful for non-INSTITUTION roles —
    callers for `INSTITUTION` should filter by `institution_id` directly.
    """

    return await user_region_ids(db, user)
