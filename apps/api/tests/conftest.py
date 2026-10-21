from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.redis_client import get_redis
from app.db.base import Base
from app.db.session import engine
from app.main import app
from app.services.storage import ensure_bucket


@pytest_asyncio.fixture(autouse=True)
async def _clean_state() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    # This points at local dev Redis (see docs/DECISIONS.md) — flushing it is
    # fine for a test/dev sandbox but would not be in a shared environment.
    get_redis().flushdb()
    # Same for local MinIO (Phase P3): ensures the bucket exists; objects are
    # uniquely keyed per upload (see `app.services.docai.pipeline.new_s3_key`)
    # so there's no cross-test collision to clean up.
    ensure_bucket()
    yield


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
