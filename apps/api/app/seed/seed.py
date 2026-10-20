"""Seed script for local development and the demo (`uv run python -m app.seed`,
or `pnpm seed` from the repo root).

IMPLEMENTATION.md §18.2 describes the full seed (8 regions, 120 institutions,
300 applications, 18 months of history, ...) that gets built out phase by
phase as the models it depends on land. This is Phase P1's slice: just enough
to exercise the login flow for every loginable role per that phase's
acceptance criteria — one region/state/institution, and one demo user per
role (`PUBLIC` and `FACULTY` have no `users` row; see docs/DECISIONS.md).
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_field, hash_identifier
from app.db.base import Base
from app.db.models import geo, institution, user, workflow  # noqa: F401 - registers tables
from app.db.models.enums import UNSCOPED_ROLES, InstitutionType, UserRole
from app.db.models.geo import Region, State
from app.db.models.institution import Institution
from app.db.models.user import User, UserRegion
from app.db.session import SessionLocal, engine
from app.seed.workflow_seed import seed_workflow

DEMO_OTP_NOTE = "123456 (DEMO_MODE fixed OTP)"

DEMO_USERS: list[tuple[UserRole, str, str]] = [
    (UserRole.ADMIN, "Admin Demo", "+911000000001"),
    (UserRole.BUREAU_HEAD, "Bureau Head Demo", "+911000000002"),
    (UserRole.REGIONAL_OFFICER, "Regional Officer Demo", "+911000000003"),
    (UserRole.SCRUTINY_OFFICER, "Scrutiny Officer Demo", "+911000000004"),
    (UserRole.COMMITTEE_MEMBER, "Committee Member Demo", "+911000000005"),
    (UserRole.EVC_EXPERT, "EVC Expert Demo", "+911000000006"),
    (UserRole.INSTITUTION, "Institution Nodal Officer Demo", "+911000000007"),
]


async def _get_or_create_region(
    db: AsyncSession, *, code: str, name: str, office_city: str
) -> Region:
    result = await db.execute(select(Region).where(Region.code == code))
    region = result.scalar_one_or_none()
    if region is None:
        region = Region(code=code, name=name, office_city=office_city)
        db.add(region)
        await db.flush()
    return region


async def _get_or_create_state(
    db: AsyncSession, *, code: str, name: str, region_id: object
) -> State:
    result = await db.execute(select(State).where(State.code == code))
    state = result.scalar_one_or_none()
    if state is None:
        state = State(code=code, name=name, region_id=region_id)
        db.add(state)
        await db.flush()
    return state


async def _get_or_create_institution(
    db: AsyncSession, *, state: State, region: Region
) -> Institution:
    aicte_id = "DEMO-0001"
    result = await db.execute(select(Institution).where(Institution.aicte_id == aicte_id))
    inst = result.scalar_one_or_none()
    if inst is None:
        inst = Institution(
            aicte_id=aicte_id,
            name="Government Engineering College, Demo City",
            type=InstitutionType.GOVT,
            state_id=state.id,
            region_id=region.id,
            city="Hyderabad",
            address="Demo Campus Road, Hyderabad",
            lat=17.385044,
            lng=78.486671,
        )
        db.add(inst)
        await db.flush()
    return inst


async def _get_or_create_user(
    db: AsyncSession,
    *,
    role: UserRole,
    name: str,
    phone: str,
    institution_id: object | None,
    region_id: object,
) -> User:
    phone_hash = hash_identifier(phone)
    result = await db.execute(select(User).where(User.phone_hash == phone_hash, User.role == role))
    demo_user = result.scalar_one_or_none()
    if demo_user is None:
        demo_user = User(
            role=role,
            name=name,
            phone_enc=encrypt_field(phone),
            phone_hash=phone_hash,
            institution_id=institution_id,
        )
        db.add(demo_user)
        await db.flush()

    if role not in UNSCOPED_ROLES:
        existing = await db.execute(
            select(UserRegion).where(
                UserRegion.user_id == demo_user.id, UserRegion.region_id == region_id
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(UserRegion(user_id=demo_user.id, region_id=region_id))

    return demo_user


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        region = await _get_or_create_region(
            db, code="HYD", name="Hyderabad Region", office_city="Hyderabad"
        )
        state = await _get_or_create_state(db, code="TG", name="Telangana", region_id=region.id)
        inst = await _get_or_create_institution(db, state=state, region=region)

        users_by_role: dict[UserRole, User] = {}
        for role, name, phone in DEMO_USERS:
            users_by_role[role] = await _get_or_create_user(
                db,
                role=role,
                name=name,
                phone=phone,
                institution_id=inst.id if role == UserRole.INSTITUTION else None,
                region_id=region.id,
            )

        await db.commit()

        await seed_workflow(db, institution=inst, users_by_role=users_by_role)

    print("Seed complete.\n")
    print(f"{'Role':<20} {'Phone':<18} OTP")
    for role, _name, phone in DEMO_USERS:
        print(f"{role.value:<20} {phone:<18} {DEMO_OTP_NOTE}")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
