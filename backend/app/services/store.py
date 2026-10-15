"""Data-access helpers, shared by the API and the MCP server.

Every function that touches a user-owned row filters by `user_id`, so one
user can never read or change another's data (CLAUDE.md 12.4, IDOR/BOLA).
Accessing a missing or foreign row returns None/False, which the API maps to
404 (never 403 — it doesn't reveal the row exists).

This is the single place DB logic lives; the MCP tools call the same
functions rather than duplicating queries (CLAUDE.md section 4).
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, FamilyContact, TrustedEntity, User
from app.pipeline.schemas import TrustedEntity as TrustedValue


# --- Users ---
async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    return await session.get(User, user_id)


async def create_user(
    session: AsyncSession, *, email: str, password_hash: str, language: str
) -> User:
    user = User(email=email.lower(), password_hash=password_hash, language=language)
    session.add(user)
    await session.flush()
    return user


# --- Trusted circle ---
async def list_trusted(session: AsyncSession, user_id: str) -> list[TrustedEntity]:
    result = await session.execute(select(TrustedEntity).where(TrustedEntity.user_id == user_id))
    return list(result.scalars().all())


async def create_trusted(
    session: AsyncSession,
    user_id: str,
    *,
    kind: str,
    name: str,
    domains: list[str],
    phones: list[str],
    emails: list[str],
) -> TrustedEntity:
    entity = TrustedEntity(
        user_id=user_id,
        kind=kind,
        name=name,
        domains=domains,
        phones=phones,
        emails=emails,
    )
    session.add(entity)
    await session.flush()
    return entity


async def get_trusted(session: AsyncSession, user_id: str, entity_id: str) -> TrustedEntity | None:
    entity = await session.get(TrustedEntity, entity_id)
    if entity is None or entity.user_id != user_id:
        return None
    return entity


async def update_trusted(
    session: AsyncSession,
    user_id: str,
    entity_id: str,
    *,
    kind: str,
    name: str,
    domains: list[str],
    phones: list[str],
    emails: list[str],
) -> TrustedEntity | None:
    entity = await get_trusted(session, user_id, entity_id)
    if entity is None:
        return None
    entity.kind = kind
    entity.name = name
    entity.domains = domains
    entity.phones = phones
    entity.emails = emails
    await session.flush()
    return entity


async def delete_trusted(session: AsyncSession, user_id: str, entity_id: str) -> bool:
    entity = await get_trusted(session, user_id, entity_id)
    if entity is None:
        return False
    await session.delete(entity)
    await session.flush()
    return True


def to_pipeline_trusted(entities: list[TrustedEntity]) -> list[TrustedValue]:
    """Convert ORM rows to the pipeline's value objects."""
    return [
        TrustedValue(
            kind=e.kind,  # type: ignore[arg-type]
            name=e.name,
            domains=list(e.domains or []),
            phones=list(e.phones or []),
            emails=list(e.emails or []),
        )
        for e in entities
    ]


# --- Family contacts ---
async def list_family(session: AsyncSession, user_id: str) -> list[FamilyContact]:
    result = await session.execute(select(FamilyContact).where(FamilyContact.user_id == user_id))
    return list(result.scalars().all())


async def create_family(
    session: AsyncSession,
    user_id: str,
    *,
    name: str,
    email: str,
    relationship_label: str,
) -> FamilyContact:
    contact = FamilyContact(
        user_id=user_id,
        name=name,
        email=email,
        relationship_label=relationship_label,
    )
    session.add(contact)
    await session.flush()
    return contact


async def get_family(session: AsyncSession, user_id: str, contact_id: str) -> FamilyContact | None:
    contact = await session.get(FamilyContact, contact_id)
    if contact is None or contact.user_id != user_id:
        return None
    return contact


async def delete_family(session: AsyncSession, user_id: str, contact_id: str) -> bool:
    contact = await get_family(session, user_id, contact_id)
    if contact is None:
        return False
    await session.delete(contact)
    await session.flush()
    return True


# --- Alerts ---
async def create_alert(
    session: AsyncSession,
    user_id: str,
    *,
    family_contact_id: str,
    risk_level: str,
    sent_ok: bool,
) -> Alert:
    alert = Alert(
        user_id=user_id,
        family_contact_id=family_contact_id,
        risk_level=risk_level,
        sent_ok=sent_ok,
    )
    session.add(alert)
    await session.flush()
    return alert


async def delete_user_data(session: AsyncSession, user_id: str) -> None:
    """Wipe a user's owned rows (used to reset the demo account)."""
    await session.execute(delete(Alert).where(Alert.user_id == user_id))
    await session.execute(delete(FamilyContact).where(FamilyContact.user_id == user_id))
    await session.execute(delete(TrustedEntity).where(TrustedEntity.user_id == user_id))
    await session.flush()
