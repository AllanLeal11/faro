"""Authentication: Argon2id password hashing and signed JWTs.

Security (CLAUDE.md 12.3):
- Passwords are hashed with Argon2id (argon2-cffi defaults).
- JWTs are short-lived, signed HS256 with a fixed algorithm (the `none`
  algorithm and algorithm-confusion are rejected by pinning algorithms), and
  carry and verify `exp`, `iss` and `aud`.
- In production a strong JWT_SECRET is required (config fails closed). In
  development, if none is set, an ephemeral per-process secret is generated so
  tokens work within a run without shipping a hardcoded key.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import get_settings

_ALGORITHM = "HS256"
_ISSUER = "faro"
_AUDIENCE = "faro-api"
_TOKEN_TTL = timedelta(hours=2)

_ph = PasswordHasher()
# Generated once per process; only used when JWT_SECRET is empty (dev only —
# production requires JWT_SECRET via the fail-closed config validator).
_EPHEMERAL_SECRET = secrets.token_urlsafe(64)


class AuthError(Exception):
    """Raised when a token is missing, invalid or expired."""


def _secret() -> str:
    return get_settings().jwt_secret or _EPHEMERAL_SECRET


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, Exception):  # noqa: BLE001 — any failure = no match
        return False


def create_access_token(user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iss": _ISSUER,
        "aud": _AUDIENCE,
        "iat": now,
        "exp": now + _TOKEN_TTL,
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def decode_token(token: str) -> str:
    """Return the user id (`sub`) from a valid token, or raise AuthError."""
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=[_ALGORITHM],  # pin: rejects "none" and other algs
            audience=_AUDIENCE,
            issuer=_ISSUER,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid or expired token.") from exc

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise AuthError("Token missing subject.")
    return sub
