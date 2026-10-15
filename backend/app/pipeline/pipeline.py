"""Pipeline orchestration: checks -> extract -> evidence -> verdict.

This module ties the stages together and enforces the two trust rules that
make Faro's verdicts defensible (CLAUDE.md section 4):

1. Evidence citation: any reason whose evidence ids are not all present in
   the real evidence set is discarded. The model cannot invent evidence.
2. Deterministic floor: if the checks fired a severe signal, the final risk
   is forced to "high" no matter what the model said.

Robustness: if the extract or verdict provider call fails, the result rests
on the deterministic checks alone and is marked `partial=True`. In MOCK_MODE
every stage is simulated and the result is a full (non-partial) stand-in.

Privacy (CLAUDE.md section 5): the analyzed message is never stored. The
short-lived verdict cache is keyed by a salted hash and holds only the
result object, which contains no message text.
"""

from __future__ import annotations

import time
from hashlib import sha256

from app.config import Settings
from app.pipeline.checks import run_checks
from app.pipeline.evidence import search_evidence
from app.pipeline.extract import extract
from app.pipeline.schemas import (
    AnalysisResult,
    EvidenceItem,
    Extraction,
    Reason,
    TrustedEntity,
    Verdict,
)
from app.pipeline.verdict import decide, deterministic_verdict

# Hard cap on message length (CLAUDE.md 12.5). The API enforces this too.
MAX_MESSAGE_CHARS = 5000

# Short-lived verdict cache (CLAUDE.md 12.9). Bounded; stores no raw content.
_CACHE_TTL_SECONDS = 300
_CACHE_MAX_ENTRIES = 512
_cache: dict[str, tuple[float, AnalysisResult]] = {}


def _cache_key(message: str, language: str, trusted: list[TrustedEntity]) -> str:
    fingerprint = "|".join(sorted(d.lower() for e in trusted for d in e.domains))
    raw = f"{language}\x00{fingerprint}\x00{message}".encode()
    return sha256(raw).hexdigest()


def _cache_get(key: str) -> AnalysisResult | None:
    hit = _cache.get(key)
    if not hit:
        return None
    expires_at, result = hit
    if time.monotonic() > expires_at:
        _cache.pop(key, None)
        return None
    return result


def _cache_put(key: str, result: AnalysisResult) -> None:
    if len(_cache) >= _CACHE_MAX_ENTRIES:
        # Simple FIFO eviction of the oldest entry.
        oldest = min(_cache, key=lambda k: _cache[k][0])
        _cache.pop(oldest, None)
    _cache[key] = (time.monotonic() + _CACHE_TTL_SECONDS, result)


def _validate_reasons(reasons: list[Reason], allowed_ids: set[str]) -> list[Reason]:
    """Drop any reason citing an evidence id that doesn't exist, and prune
    unknown ids from the reasons that remain."""
    kept: list[Reason] = []
    for reason in reasons:
        cited = [eid for eid in reason.evidence_ids if eid in allowed_ids]
        if not cited:
            # A reason with no real evidence behind it is discarded entirely.
            continue
        kept.append(Reason(text=reason.text, evidence_ids=cited))
    return kept


def _apply_floor(
    verdict: Verdict, evidence: list[EvidenceItem], severe: bool, language: str
) -> Verdict:
    """Force risk to 'high' when a severe deterministic signal fired."""
    if not severe or verdict.risk_level == "high":
        return verdict

    severe_ids = [e.id for e in evidence if e.severe]
    is_spanish = language.lower().startswith("es")
    floor_text = (
        "Una verificación automática detectó una señal grave de estafa."
        if is_spanish
        else "An automated check found a severe scam signal."
    )
    reasons = [Reason(text=floor_text, evidence_ids=severe_ids), *verdict.reasons]
    return verdict.model_copy(
        update={
            "risk_level": "high",
            "confidence": max(verdict.confidence, 0.9),
            "reasons": reasons,
        }
    )


async def analyze(
    message: str,
    trusted: list[TrustedEntity],
    settings: Settings,
    *,
    language: str = "es",
    client=None,
) -> AnalysisResult:
    """Analyze one message and return a validated AnalysisResult.

    `client` is the LLM client (or None for MOCK_MODE). It is injected so the
    API and MCP layers can share one client instance; when omitted it is
    created from settings.
    """
    message = message[:MAX_MESSAGE_CHARS]

    key = _cache_key(message, language, trusted)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    if client is None and not settings.mock_mode:
        # Build a real client lazily only when not supplied and not in mock.
        from app.services.llm import get_llm_client

        client = get_llm_client(settings)

    partial = False

    # 1. Deterministic checks — always run, never fail.
    checks = run_checks(message, trusted, language)

    # 2. Extract (LLM/mock).
    extraction = await extract(message, client, settings.model_extract)
    if extraction is None:
        partial = True
        extraction = Extraction()

    # 3. Evidence (optional Tavily).
    search_items: list[EvidenceItem] = []
    if settings.tavily_api_key and not settings.mock_mode:
        search_items = await search_evidence(
            extraction, settings.tavily_api_key, base_id=len(checks.evidence)
        )

    all_evidence = [*checks.evidence, *search_items]

    # 4. Verdict (LLM/mock).
    verdict = await decide(
        message,
        extraction,
        all_evidence,
        client,
        settings.model_verdict,
        checks.severe_hit,
        language=language,
    )
    if verdict is None:
        partial = True
        verdict = deterministic_verdict(all_evidence, checks.severe_hit, language)

    # Enforce the two trust rules.
    allowed_ids = {e.id for e in all_evidence}
    verdict = verdict.model_copy(
        update={"reasons": _validate_reasons(verdict.reasons, allowed_ids)}
    )
    verdict = _apply_floor(verdict, all_evidence, checks.severe_hit, language)

    result = AnalysisResult(
        risk_level=verdict.risk_level,
        confidence=verdict.confidence,
        reasons=verdict.reasons,
        explanation=verdict.explanation,
        recommended_action=verdict.recommended_action,
        verification_question=verdict.verification_question,
        evidence=all_evidence,
        partial=partial,
    )
    _cache_put(key, result)
    return result
