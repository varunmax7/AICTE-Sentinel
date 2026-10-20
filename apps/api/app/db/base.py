from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. Every model module registers its tables on this
    metadata by importing from here; `app.db.models` imports every module so
    Alembic autogenerate and `Base.metadata.create_all` (tests) see them all.
    """
