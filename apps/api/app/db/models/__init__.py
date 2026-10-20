"""Import every model module so `Base.metadata` is complete for Alembic
autogenerate and for `Base.metadata.create_all` in tests.
"""

from app.db.models import audit, geo, institution, otp, outbox, user  # noqa: F401

__all__ = ["audit", "geo", "institution", "otp", "outbox", "user"]
