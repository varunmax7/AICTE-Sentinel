import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin
from app.db.models.enums import InstitutionType


class Institution(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "institutions"

    aicte_id: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(256))
    type: Mapped[InstitutionType] = mapped_column(Enum(InstitutionType, name="institution_type"))
    state_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("states.id"))
    region_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regions.id"))
    city: Mapped[str] = mapped_column(String(128))
    address: Mapped[str] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    geofence_radius_m: Mapped[int] = mapped_column(Integer, default=300)
    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    contacts: Mapped[list["InstitutionContact"]] = relationship(back_populates="institution")


class InstitutionContact(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "institution_contacts"

    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id"))
    name: Mapped[str] = mapped_column(String(256))
    designation: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    email_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    whatsapp_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    call_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_call_time: Mapped[str | None] = mapped_column(String(32), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")
    is_nodal: Mapped[bool] = mapped_column(Boolean, default=False)

    institution: Mapped["Institution"] = relationship(back_populates="contacts")
