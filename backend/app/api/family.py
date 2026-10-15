"""Family-contact CRUD (CLAUDE.md 12.4: every row scoped to the owner)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import FamilyCreate, FamilyOut
from app.db.base import get_session
from app.db.models import User
from app.services import store

router = APIRouter(prefix="/api/family", tags=["family"])

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")


def _to_out(contact) -> FamilyOut:
    return FamilyOut(
        id=contact.id,
        name=contact.name,
        email=contact.email,
        relationship_label=contact.relationship_label,
    )


@router.get("", response_model=list[FamilyOut])
async def list_family(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[FamilyOut]:
    contacts = await store.list_family(session, user.id)
    return [_to_out(c) for c in contacts]


@router.post("", response_model=FamilyOut, status_code=status.HTTP_201_CREATED)
async def create_family(
    body: FamilyCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FamilyOut:
    contact = await store.create_family(
        session,
        user.id,
        name=body.name,
        email=str(body.email),
        relationship_label=body.relationship_label,
    )
    await session.commit()
    return _to_out(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_family(
    contact_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    ok = await store.delete_family(session, user.id, contact_id)
    if not ok:
        raise _NOT_FOUND
    await session.commit()
