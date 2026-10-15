"""Tests for the deterministic check stage (app.pipeline.checks).

These need no API keys and form the security floor's regression suite
(CLAUDE.md sections 12.5, 12.7, 12.12). They assert both detection and the
`severe_hit` floor that the LLM verdict may not lower.
"""

from __future__ import annotations

from app.pipeline.checks import defang, normalize, run_checks
from app.pipeline.schemas import TrustedEntity

# A small trusted circle mirroring the demo persona: a Costa Rican bank.
BAC = TrustedEntity(
    kind="bank",
    name="BAC Credomatic",
    domains=["baccredomatic.com"],
    phones=["2295-9898"],
    emails=["info@baccredomatic.com"],
)


def _types(result) -> set[str]:
    return {e.type for e in result.evidence}


def test_clean_message_has_no_severe_hit():
    msg = "Hola mama, nos vemos el domingo para el almuerzo. Te quiero."
    result = run_checks(msg, [BAC])
    assert result.severe_hit is False
    assert result.evidence == []


def test_otp_request_is_severe():
    msg = "BAC: su codigo de verificacion es 884120. No comparta este codigo."
    result = run_checks(msg, [BAC])
    assert result.severe_hit is True
    assert "otp_request" in _types(result)


def test_gift_card_and_crypto_is_severe():
    msg = "Felicidades! Pague con una gift card de iTunes para reclamar su premio."
    result = run_checks(msg, [BAC])
    assert result.severe_hit is True
    assert "giftcard_or_crypto" in _types(result)


def test_lookalike_domain_is_severe():
    # One character off the trusted domain.
    msg = "Ingrese a https://baccredomatlc.com/login para validar su cuenta."
    result = run_checks(msg, [BAC])
    assert result.severe_hit is True
    assert "lookalike_domain" in _types(result)


def test_brand_token_on_wrong_domain_is_flagged():
    msg = "Verifique en https://bac-seguro-cr.com su informacion."
    result = run_checks(msg, [BAC])
    assert "sender_mismatch" in _types(result)
    assert result.severe_hit is True


def test_ip_url_is_flagged_not_severe_alone():
    msg = "Actualice aqui: http://203.0.113.9/update"
    result = run_checks(msg, [BAC])
    assert "ip_url" in _types(result)


def test_url_shortener_is_flagged():
    msg = "Reclame su premio: https://bit.ly/3xAbCdE ahora."
    result = run_checks(msg, [BAC])
    assert "url_shortener" in _types(result)


def test_punycode_domain_is_severe():
    msg = "Acceda a https://xn--bac-9na.com/verificar"
    result = run_checks(msg, [BAC])
    assert "punycode_domain" in _types(result)
    assert result.severe_hit is True


def test_homoglyph_domain_is_severe():
    # Cyrillic 'а' (U+0430) replacing the Latin 'a' in the host.
    msg = "Ingrese a https://bаccredomatic.com/login"
    result = run_checks(msg, [BAC])
    assert "homoglyph_domain" in _types(result)
    assert result.severe_hit is True


def test_bidi_control_is_flagged():
    # U+202E (RLO) hidden in the text.
    msg = "Su factura‮ gpj.exe esta lista."
    result = run_checks(msg, [BAC])
    assert "bidi_trick" in _types(result)


def test_urgency_is_flagged_not_severe_alone():
    msg = "URGENTE: su cuenta sera bloqueada. Responda inmediatamente."
    result = run_checks(msg, [BAC])
    assert "urgency_pressure" in _types(result)
    # Urgency by itself is pressure, not a severe floor.
    severe_types = {e.type for e in result.evidence if e.severe}
    assert "urgency_pressure" not in severe_types


def test_defang_never_produces_clickable_scheme():
    out = defang("https://banco-falso.com/login")
    assert "http://" not in out
    assert "https://" not in out
    assert out == "hxxps://banco-falso[.]com/login"


def test_normalize_strips_zero_width():
    assert normalize("pa​go") == "pago"


def test_no_trusted_circle_still_detects_intent():
    # Even with an empty trusted circle, intent checks still fire.
    msg = "Comparta su codigo OTP para desbloquear su cuenta."
    result = run_checks(msg, [])
    assert result.severe_hit is True
    assert "otp_request" in _types(result)
