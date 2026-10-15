"""Async SQLAlchemy engine, session factory and base class.

Portable across SQLite (local dev / tests) and PostgreSQL (Railway). The
connection string comes from Settings.effective_database_url, which already
normalizes Railway's `postgresql://` to the asyncpg driver.

Security (CLAUDE.md 12.2, 12.5):
- All data access goes through the ORM with bound parameters — never string
  concatenation into SQL.
- For PostgreSQL, libpq-style query params that asyncpg rejects (sslmode,
  channel_binding) are translated to connect_args, and TLS is enabled when
  the URL asks for it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _prepare_url(url: str) -> tuple[str, dict]:
    """Split out asyncpg-incompatible query params and derive connect_args."""
    if not url.startswith("postgresql+asyncpg://"):
        return url, {}

    parts = urlsplit(url)
    query = parse_qs(parts.query)
    connect_args: dict = {}

    sslmode = query.pop("sslmode", [None])[0]
    query.pop("channel_binding", None)
    if sslmode in {"require", "verify-ca", "verify-full"}:
        connect_args["ssl"] = True

    cleaned = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment)
    )
    return cleaned, connect_args


_settings = get_settings()
_url, _connect_args = _prepare_url(_settings.effective_database_url)

engine = create_async_engine(
    _url,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a database session."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create tables if they don't exist (dev/demo convenience).

    Production migrations would use Alembic; for the hackathon demo the schema
    is created at startup and the demo account is seeded (see db/seed.py).
    """
    # Import models so they are registered on Base.metadata before create_all.
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
