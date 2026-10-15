"""Shared data shapes for the analysis pipeline.

These models are the contract between the pipeline stages (extract, checks,
evidence, verdict) and the API/MCP layers. They are deliberately decoupled
from the database models: the pipeline never touches persistence, and the
trusted-circle data it needs is passed in as plain value objects.

Security notes (CLAUDE.md section 12):
- Every model forbids extra fields (`extra="forbid"`) so a malformed or
  adversarial LLM/JSON payload can't smuggle in unexpected keys.
- The analyzed message itself is never stored on any of these models beyond
  the single in-memory request; nothing here is persisted.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["low", "medium", "high"]

# Actions a scam typically asks the victim to take. Kept as a closed set so
# the verdict stage reasons over known categories rather than free text.
RequestedAction = Literal[
    "pay",
    "click",
    "share_code",
    "install_app",
    "provide_credentials",
    "none",
    "unknown",
]


class TrustedEntity(BaseModel):
    """A value object for one entry in the user's trusted circle.

    This is the pipeline-facing view of a `trusted_entities` row — just the
    fields the deterministic checks need, with no user_id or DB identity.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["bank", "company", "contact"]
    name: str
    domains: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)


class Extraction(BaseModel):
    """Structured fields pulled from the message by the extract stage (LLM).

    The LLM output is validated against this schema and rejected if invalid
    (CLAUDE.md section 12.7, "structured output"). The deterministic checks
    do NOT depend on this — they re-derive URLs/domains/phones/emails from the
    raw text themselves, so the pipeline still works if the LLM fails.
    """

    model_config = ConfigDict(extra="forbid")

    urls: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    # The organization the message claims to be from (e.g. "BAC Credomatic").
    claimed_sender: str | None = None
    requested_action: RequestedAction = "unknown"
    # Free-form pressure tactics detected: "urgency", "threat", "prize", etc.
    pressure_signals: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    """One piece of evidence, from either a deterministic check or a search.

    `id` is a short stable handle (e.g. "chk-1", "ev-2") that the verdict
    stage must cite in its reasons. Any reason citing an id that is not in
    the evidence set is discarded by the pipeline — the model cannot invent
    evidence (CLAUDE.md section 4, "regla clave").
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    # "check" for deterministic findings, "search" for Tavily results.
    kind: Literal["check", "search"]
    # For checks: the check type, e.g. "lookalike_domain". For search: "search".
    type: str
    # "hit" / "clear" for checks; a short label for search results.
    result: str
    # Human-readable detail. For checks, URLs are already defanged.
    detail: str
    # Only set for search evidence: the official source URL (https only).
    source_url: str | None = None
    # Severe deterministic hits set a floor the LLM cannot lower below "high".
    severe: bool = False


class ChecksOutput(BaseModel):
    """Result of the deterministic checks stage."""

    model_config = ConfigDict(extra="forbid")

    evidence: list[EvidenceItem] = Field(default_factory=list)
    # True if any severe signal fired (lookalike domain, OTP/credential
    # request, gift-card/crypto payment demand). Forces risk >= high.
    severe_hit: bool = False
    # Defanged forms of every URL found, safe to show in the UI as text.
    defanged_urls: list[str] = Field(default_factory=list)


class Reason(BaseModel):
    """One reason behind the verdict, with the evidence ids that back it."""

    model_config = ConfigDict(extra="forbid")

    text: str
    evidence_ids: list[str] = Field(default_factory=list)


class Verdict(BaseModel):
    """The reasoning stage's structured output (validated LLM response)."""

    model_config = ConfigDict(extra="forbid")

    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[Reason] = Field(default_factory=list)
    explanation: str
    recommended_action: str
    verification_question: str


class AnalysisResult(BaseModel):
    """The final result returned by the pipeline to the API/MCP layer.

    This is what the user ultimately sees. It merges the verdict with the
    evidence set and the robustness flag.
    """

    model_config = ConfigDict(extra="forbid")

    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[Reason] = Field(default_factory=list)
    explanation: str
    recommended_action: str
    verification_question: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    # True when a provider (LLM or Tavily) failed and the result rests on the
    # deterministic checks alone (CLAUDE.md section 4, "robustez").
    partial: bool = False
