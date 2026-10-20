from sqlalchemy import select

from app.db.models.audit import AuditEvent
from app.db.models.enums import ActorType
from app.db.session import SessionLocal
from app.services.audit.chain import verify_chain, write_audit_event


async def test_audit_chain_links_and_verifies() -> None:
    async with SessionLocal() as db:
        await write_audit_event(
            db, actor_type=ActorType.SYSTEM, actor_id=None, action="test.one", entity_type="test"
        )
        await write_audit_event(
            db, actor_type=ActorType.SYSTEM, actor_id=None, action="test.two", entity_type="test"
        )
        await db.commit()

    async with SessionLocal() as db:
        ok, broken_at = await verify_chain(db)
        assert ok
        assert broken_at is None


async def test_audit_chain_detects_tampering() -> None:
    async with SessionLocal() as db:
        await write_audit_event(
            db, actor_type=ActorType.SYSTEM, actor_id=None, action="test.one", entity_type="test"
        )
        await db.commit()

    async with SessionLocal() as db:
        result = await db.execute(select(AuditEvent))
        row = result.scalar_one()
        row.action = "tampered"
        tampered_id = row.id
        await db.commit()

    async with SessionLocal() as db:
        ok, broken_at = await verify_chain(db)
        assert not ok
        assert broken_at == tampered_id
