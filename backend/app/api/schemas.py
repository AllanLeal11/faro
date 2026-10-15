"""API request/response schemas.

Security (CLAUDE.md 12.4, 12.5):
- Every request model sets `extra="forbid"` (no mass assignment) and never
  contains a `user_id` — ownership comes from the authenticated token only.
- Fields are length- and format-bounded; emails use EmailStr; domains and
  phones are normalized and validated.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

MAX_MESSAGE_CHARS = 5000

_DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z0-9\-]{1,63})+$")
_PHONE_RE = re.compile(r"^\+?[0-9\s\-().]{7,20}$")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Auth ---
class RegisterRequest(_Strict):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    language: Literal["es", "en"] = "es"


class LoginRequest(_Strict):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(_Strict):
    id: str
    email: EmailStr
    language: str


class TokenResponse(_Strict):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 — OAuth type, not a secret
    user: UserOut


# --- Check ---
class CheckRequest(_Strict):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    language: Literal["es", "en"] | None = None


# --- Trusted circle ---
class TrustedBase(_Strict):
    kind: Literal["bank", "company", "contact"]
    name: str = Field(min_length=1, max_length=200)
    domains: list[str] = Field(default_factory=list, max_length=20)
    phones: list[str] = Field(default_factory=list, max_length=20)
    emails: list[EmailStr] = Field(default_factory=list, max_length=20)

    @field_validator("domains")
    @classmethod
    def _check_domains(cls, value: list[str]) -> list[str]:
        out = []
        for d in value:
            d = d.strip().lower()
            if not _DOMAIN_RE.match(d):
                raise ValueError(f"Invalid domain: {d!r}")
            out.append(d)
        return out

    @field_validator("phones")
    @classmethod
    def _check_phones(cls, value: list[str]) -> list[str]:
        out = []
        for p in value:
            p = p.strip()
            if not _PHONE_RE.match(p):
                raise ValueError(f"Invalid phone: {p!r}")
            out.append(p)
        return out


class TrustedCreate(TrustedBase):
    pass


class TrustedUpdate(TrustedBase):
    pass


class TrustedOut(TrustedBase):
    id: str


# --- Family contacts ---
class FamilyCreate(_Strict):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    relationship_label: str = Field(default="", max_length=64)


class FamilyOut(_Strict):
    id: str
    name: str
    email: EmailStr
    relationship_label: str


# --- Alerts ---
class AlertRequest(_Strict):
    family_contact_id: str = Field(min_length=1, max_length=64)
    risk_level: Literal["low", "medium", "high"]
    verification_question: str = Field(default="", max_length=500)


class AlertResponse(_Strict):
    id: str
    sent_ok: bool
