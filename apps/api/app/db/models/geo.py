import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin


class Region(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "regions"

    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    office_city: Mapped[str] = mapped_column(String(128))

    states: Mapped[list["State"]] = relationship(back_populates="region")


class State(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "states"

    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    region_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regions.id"))

    region: Mapped["Region"] = relationship(back_populates="states")
