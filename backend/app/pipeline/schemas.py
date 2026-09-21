"""Shared data contracts for the analysis pipeline (CLAUDE.md section 4).

`ExtractedMessage` is what extract.py (Nemotron Nano) will produce; checks.py
consumes it today so the deterministic checks can be built and tested before
extract.py exists. `TrustedEntity` mirrors the columns of the
`trusted_entities` table (section 4, database schema) that the user's
trusted circle is read from.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PressureSignal = Literal["urgency", "threat", "prize"]
RequestedAction = Literal["pay", "click_link", "share_code", "install_app", "other"]
PaymentMethod = Literal["otp_code", "gift_card", "cryptocurrency", "bank_transfer"]
EvidenceResult = Literal["clear", "suspicious", "severe"]


class TrustedEntity(BaseModel):
    """One entry of the user's trusted circle (bank, company or contact)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["bank", "company", "contact"]
    name: str
    domains: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)


class ExtractedMessage(BaseModel):
    """Structured facts extracted from a suspicious message by extract.py.

    Never holds the raw message text: checks.py only ever sees the facts
    extract.py pulled out of it (CLAUDE.md section 5, privacy).
    """

    model_config = ConfigDict(extra="forbid")

    urls: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    claimed_org: str | None = None
    requested_action: RequestedAction | None = None
    payment_methods_requested: list[PaymentMethod] = Field(default_factory=list)
    pressure_signals: list[PressureSignal] = Field(default_factory=list)


class Evidence(BaseModel):
    """One piece of evidence produced by a deterministic check or by Tavily.

    verdict.py (CLAUDE.md section 4) may only cite `id`s that actually
    appear here — it can never invent evidence.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    result: EvidenceResult
    detail: str
