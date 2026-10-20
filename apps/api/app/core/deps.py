"""RBAC + region-scope dependencies (IMPLEMENTATION.md §17). Every
state-changing / data-reading router depends on `get_current_user` (or
`require(...)` for a role check); list-style repository queries additionally
call `user_region_ids` to filter by the caller's assigned regions, unless
they hold an unscoped role (`BUREAU_HEAD`, `ADMIN` — see §2.1).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import ACCESS_COOKIE, decode_token
from app.db.models.enums import UNSCOPED_ROLES, UserRole
from app.db.models.user import User, UserRegion
from app.db.session import get_db


async def get_current_user(
    *,
    acp_access: str | None = Cookie(default=None, alias=ACCESS_COOKIE),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not acp_access:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "NOT_AUTHENTICATED"})
    try:
        payload = decode_token(acp_access)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_TOKEN"}) from exc
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_TOKEN_TYPE"})

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "USER_NOT_FOUND"})
    return user


def require(*roles: UserRole) -> Any:
    """`Depends(require(UserRole.SCRUTINY_OFFICER, UserRole.REGIONAL_OFFICER))`
    — no roles means "any authenticated user".
    """

    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if roles and user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ROLE_NOT_ALLOWED",
                    "params": {"required": [r.value for r in roles], "actual": user.role.value},
                },
            )
        return user

    return _dependency


async def user_region_ids(db: AsyncSession, user: User) -> Sequence[uuid.UUID] | None:
    """`None` means unscoped (sees every region) — BUREAU_HEAD and ADMIN."""
    if user.role in UNSCOPED_ROLES:
        return None
    result = await db.execute(select(UserRegion.region_id).where(UserRegion.user_id == user.id))
    return list(result.scalars())
