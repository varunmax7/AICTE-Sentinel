"""`ocr_extract` Celery task (IMPLEMENTATION.md §13.4, §14). Not invoked by
the upload endpoint in this phase — see `app.services.docai.pipeline`'s
docstring for why — but available for any future non-HTTP trigger of the
same extraction pipeline.
"""

from __future__ import annotations

import asyncio
import uuid

from app.db.session import SessionLocal
from app.services.docai.pipeline import run_extraction
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.docai.ocr_extract")
def ocr_extract(document_version_id: str) -> str:
    return asyncio.run(_ocr_extract_async(document_version_id))


async def _ocr_extract_async(document_version_id: str) -> str:
    from app.db.models.documents import DocumentVersion

    async with SessionLocal() as db:
        version = await db.get(DocumentVersion, uuid.UUID(document_version_id))
        if version is None:
            return "NOT_FOUND"
        extraction = await run_extraction(db, version)
        return str(extraction.id)
