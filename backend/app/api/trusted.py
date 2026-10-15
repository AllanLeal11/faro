"""Trusted-circle CRUD (CLAUDE.md 12.4: every row scoped to the owner)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import TrustedCreate, TrustedOut, TrustedUpdate
from app.db.base import get_session
from app.db.models import User
from app.services import store

router = APIRouter(prefix="/api/trusted", tags=["trusted"])

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")


def _to_out(entity) -> TrustedOut:
    return TrustedOut(
        id=entity.id,
        kind=entity.kind,
        name=entity.name,
        domains=list(entity.domains or []),
        phones=list(entity.phones or []),
        emails=list(entity.emails or []),
    )


@router.get("", response_model=list[TrustedOut])
async def list_trusted(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TrustedOut]:
    entities = await store.list_trusted(session, user.id)
    return [_to_out(e) for e in entities]


@router.post("", response_model=TrustedOut, status_code=status.HTTP_201_CREATED)
async def create_trusted(
    body: TrustedCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TrustedOut:
    entity = await store.create_trusted(
        session,
        user.id,
        kind=body.kind,
        name=body.name,
        domains=body.domains,
        phones=body.phones,
        emails=[str(e) for e in body.emails],
    )
    await session.commit()
    return _to_out(entity)


@router.put("/{entity_id}", response_model=TrustedOut)
async def update_trusted(
    entity_id: str,
    body: TrustedUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TrustedOut:
    entity = await store.update_trusted(
        session,
        user.id,
        entity_id,
        kind=body.kind,
        name=body.name,
        domains=body.domains,
        phones=body.phones,
        emails=[str(e) for e in body.emails],
    )
    if entity is None:
        raise _NOT_FOUND
    await session.commit()
    return _to_out(entity)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trusted(
    entity_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    ok = await store.delete_trusted(session, user.id, entity_id)
    if not ok:
        raise _NOT_FOUND
    await session.commit()
