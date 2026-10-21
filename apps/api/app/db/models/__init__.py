"""Import every model module so `Base.metadata` is complete for Alembic
autogenerate and for `Base.metadata.create_all` in tests.
"""

from app.db.models import (  # noqa: F401
    audit,
    deadline,
    documents,
    geo,
    institution,
    otp,
    outbox,
    user,
    workflow,
)

__all__ = [
    "audit",
    "deadline",
    "documents",
    "geo",
    "institution",
    "otp",
    "outbox",
    "user",
    "workflow",
]
