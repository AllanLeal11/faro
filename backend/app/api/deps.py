"""FastAPI dependencies: authentication and client identity.

Auth uses a Bearer token (held in memory by the SPA, never in localStorage,
and used by the MCP server as a per-user token). This is a deliberate choice
over a cookie+CSRF scheme because the frontend (Vercel) and backend (Railway)
live on different domains, where a SameSite cookie would not be sent; a
memory-only Bearer token avoids ambient-cookie CSRF entirely. See
docs/security.md. (CLAUDE.md 12.3)
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session
from app.db.models import User
from app.services import store
from app.services.auth import AuthError, decode_token

_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated.",
    headers={"WWW-Authenticate": "Bearer"},
)


def client_ip(request: Request) -> str:
    """Best-effort client IP for rate-limiting keys.

    Railway terminates TLS and appends the real peer IP as the rightmost
    X-Forwarded-For entry, so that entry is used when present; otherwise the
    direct socket peer. Used only for rate limiting, never for authz.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return request.client.host if request.client else "unknown"


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _UNAUTH
    token = authorization[7:].strip()
    try:
        user_id = decode_token(token)
    except AuthError as exc:
        raise _UNAUTH from exc

    user = await store.get_user_by_id(session, user_id)
    if user is None:
        raise _UNAUTH
    return user
