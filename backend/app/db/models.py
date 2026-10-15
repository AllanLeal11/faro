"""ORM models (CLAUDE.md section 4, database).

Privacy: analyzed messages are NEVER stored. Only the trusted circle, family
contacts and alert metadata (without message content) are persisted.

Portability: UUID hex strings are used for primary keys and JSON columns for
string lists, so the same models run on SQLite and PostgreSQL unchanged.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(8), default="es")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    trusted_entities: Mapped[list[TrustedEntity]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    family_contacts: Mapped[list[FamilyContact]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class TrustedEntity(Base):
    __tablename__ = "trusted_entities"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # bank | company | contact
    name: Mapped[str] = mapped_column(String(200))
    domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    phones: Mapped[list[str]] = mapped_column(JSON, default=list)
    emails: Mapped[list[str]] = mapped_column(JSON, default=list)

    user: Mapped[User] = relationship(back_populates="trusted_entities")


class FamilyContact(Base):
    __tablename__ = "family_contacts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320))
    relationship_label: Mapped[str] = mapped_column(String(64), default="")

    user: Mapped[User] = relationship(back_populates="family_contacts")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    family_contact_id: Mapped[str] = mapped_column(
        ForeignKey("family_contacts.id", ondelete="CASCADE")
    )
    risk_level: Mapped[str] = mapped_column(String(8))
    # Metadata only — the analyzed message is never stored here.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    sent_ok: Mapped[bool] = mapped_column(default=False)
