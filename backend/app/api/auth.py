"""Auth routes: register and login (CLAUDE.md 12.3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip
from app.api.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.db.base import get_session
from app.services import store
from app.services.auth import create_access_token, hash_password, verify_password
from app.services.ratelimit import LOGIN_PER_MINUTE, limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Generic message: never reveal whether an email exists (CLAUDE.md 12.3).
_INVALID_CREDS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid email or password.",
)
_RATE_LIMITED = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Too many attempts. Please wait a minute and try again.",
)


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    if not limiter.check(f"register:{client_ip(request)}", LOGIN_PER_MINUTE):
        raise _RATE_LIMITED

    existing = await store.get_user_by_email(session, body.email)
    if existing is not None:
        # Same generic error as a bad login, to avoid email enumeration.
        raise _INVALID_CREDS

    user = await store.create_user(
        session,
        email=body.email,
        password_hash=hash_password(body.password),
        language=body.language,
    )
    await session.commit()
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserOut(id=user.id, email=user.email, language=user.language),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    if not limiter.check(f"login:{client_ip(request)}", LOGIN_PER_MINUTE):
        raise _RATE_LIMITED

    user = await store.get_user_by_email(session, body.email)
    if user is None or not verify_password(user.password_hash, body.password):
        raise _INVALID_CREDS

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserOut(id=user.id, email=user.email, language=user.language),
    )
