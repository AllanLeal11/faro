"""Tests for pipeline orchestration (app.pipeline.pipeline).

Covers MOCK_MODE end-to-end plus the two trust rules — the deterministic
floor and evidence-citation validation — exercised through a fake LLM client
that returns canned JSON, so no API keys are needed (CLAUDE.md 4, 12.7).
"""

from __future__ import annotations

import json

import pytest

from app.config import Settings
from app.pipeline.pipeline import analyze
from app.pipeline.schemas import TrustedEntity

BAC = TrustedEntity(
    kind="bank",
    name="BAC Credomatic",
    domains=["baccredomatic.com"],
    phones=["2295-9898"],
    emails=["info@baccredomatic.com"],
)

OTP_SCAM = "BAC: su codigo de verificacion es 884120. No lo comparta con nadie."
CLEAN = "Hola mama, nos vemos el domingo para el almuerzo."


def _mock_settings(**over) -> Settings:
    base = dict(
        mock_mode=True,
        environment="development",
        model_extract="mock",
        model_verdict="mock",
    )
    base.update(over)
    return Settings(**base)


class _FakeClient:
    """An LLM client that returns canned JSON per stage, for testing the
    real-client code path (floor + citation validation)."""

    def __init__(self, verdict_json: dict) -> None:
        self._verdict_json = verdict_json

    async def generate(
        self, *, system: str, user: str, model: str, max_tokens: int, temperature: float = 0.0
    ) -> str:
        if "extraction stage" in system:
            return json.dumps(
                {
                    "urls": [],
                    "domains": [],
                    "phones": [],
                    "emails": [],
                    "claimed_sender": "BAC Credomatic",
                    "requested_action": "share_code",
                    "pressure_signals": ["urgency"],
                }
            )
        return json.dumps(self._verdict_json)


@pytest.mark.asyncio
async def test_mock_mode_flags_otp_scam_as_high():
    result = await analyze(OTP_SCAM, [BAC], _mock_settings(), language="es")
    assert result.risk_level == "high"
    assert result.partial is False
    assert any(e.type == "otp_request" for e in result.evidence)
    # Every reason cites real evidence.
    ids = {e.id for e in result.evidence}
    for reason in result.reasons:
        assert reason.evidence_ids
        assert set(reason.evidence_ids) <= ids


@pytest.mark.asyncio
async def test_mock_mode_clean_message_is_low():
    result = await analyze(CLEAN, [BAC], _mock_settings(), language="es")
    assert result.risk_level == "low"
    assert result.partial is False


@pytest.mark.asyncio
async def test_deterministic_floor_overrides_model_low():
    # The model wrongly says "low" on an OTP scam; the floor must force high.
    fake = _FakeClient(
        {
            "risk_level": "low",
            "confidence": 0.2,
            "reasons": [{"text": "Looks fine", "evidence_ids": []}],
            "explanation": "Seems ok.",
            "recommended_action": "Nothing.",
            "verification_question": "Is this real?",
        }
    )
    settings = _mock_settings(mock_mode=False)
    result = await analyze(OTP_SCAM, [BAC], settings, language="en", client=fake)
    assert result.risk_level == "high"
    # The floor reason cites the severe check id.
    severe_ids = {e.id for e in result.evidence if e.severe}
    assert any(set(r.evidence_ids) & severe_ids for r in result.reasons)


@pytest.mark.asyncio
async def test_invented_evidence_ids_are_discarded():
    # The model cites a non-existent evidence id; that reason is dropped.
    fake = _FakeClient(
        {
            "risk_level": "high",
            "confidence": 0.9,
            "reasons": [
                {"text": "Fabricated", "evidence_ids": ["chk-999"]},
                {"text": "Real", "evidence_ids": ["chk-1"]},
            ],
            "explanation": "High risk.",
            "recommended_action": "Do not reply.",
            "verification_question": "Call the bank.",
        }
    )
    settings = _mock_settings(mock_mode=False)
    result = await analyze(OTP_SCAM, [BAC], settings, language="en", client=fake)
    texts = [r.text for r in result.reasons]
    assert "Fabricated" not in texts
    # No surviving reason cites the invented id.
    for reason in result.reasons:
        assert "chk-999" not in reason.evidence_ids
