"""Test configuration: isolated SQLite DB, mock mode, fresh schema per test.

Environment is set before any app module is imported so the module-level
engine binds to a throwaway SQLite file and the app runs in MOCK_MODE (no
keys, simulated LLM).
"""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="faro-test-")
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("MODEL_EXTRACT", "mock")
os.environ.setdefault("MODEL_VERDICT", "mock")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMPDIR}/test.db"

import pytest_asyncio  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _fresh_db():
    """Drop and recreate all tables, and reset the rate limiter, per test."""
    from app.db.base import Base, engine
    from app.services.ratelimit import limiter

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    limiter._events.clear()
    yield


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register(client, email: str, password: str = "Sup3rSecret!") -> str:
    """Register a user and return the bearer token."""
    resp = await client.post("/api/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
