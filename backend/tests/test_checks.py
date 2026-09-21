"""Unit tests for the deterministic checks (CLAUDE.md section 13, step 4).

No API keys or network access needed: everything here is pure Python.
"""

from app.pipeline.checks import (
    check_domain_lookalike,
    check_ip_literal_url,
    check_sender_mismatch,
    check_url_shortener,
    floors_risk_high,
    run_checks,
)
from app.pipeline.schemas import ExtractedMessage, TrustedEntity

BANK = TrustedEntity(
    kind="bank",
    name="Banco Real",
    domains=["bancoreal.com"],
    phones=["+1 555 100 2000"],
    emails=["alerts@bancoreal.com"],
)


def _results(evidence, evidence_type):
    return [e.result for e in evidence if e.type == evidence_type]


class TestDomainLookalike:
    def test_exact_trusted_domain_is_clear(self):
        evidence = check_domain_lookalike(["bancoreal.com"], [BANK])
        assert len(evidence) == 1
        assert evidence[0].result == "clear"

    def test_no_domains_is_clear(self):
        evidence = check_domain_lookalike([], [BANK])
        assert evidence[0].result == "clear"

    def test_typosquat_digit_substitution_is_severe(self):
        evidence = check_domain_lookalike(["banc0real.com"], [BANK])
        assert evidence[0].result == "severe"
        assert "banc0real.com" not in evidence[0].detail  # dots must be defanged
        assert "banc0real[.]com" in evidence[0].detail

    def test_homoglyph_exact_clone_is_severe(self):
        # Cyrillic а/е/о in place of Latin a/e/o — same skeleton, different domain.
        lookalike = "bаncoрeаl.com".replace("р", "r")
        evidence = check_domain_lookalike([lookalike], [BANK])
        assert evidence[0].result == "severe"

    def test_punycode_domain_without_trusted_match_is_suspicious(self):
        evidence = check_domain_lookalike(["xn--80ak6aa92e.com"], [BANK])
        assert evidence[0].result in ("suspicious", "severe")

    def test_unrelated_domain_is_clear(self):
        evidence = check_domain_lookalike(["example.org"], [BANK])
        assert evidence[0].result == "clear"

    def test_overlong_domain_is_skipped_not_crashed(self):
        evidence = check_domain_lookalike(["a" * 300 + ".com"], [BANK])
        assert evidence[0].result == "clear"


class TestUrlShortener:
    def test_known_shortener_is_suspicious(self):
        evidence = check_url_shortener(["https://bit.ly/abc123"])
        assert evidence[0].result == "suspicious"
        assert "bit[.]ly" in evidence[0].detail

    def test_no_shortener_is_clear(self):
        evidence = check_url_shortener(["https://bancoreal.com/login"])
        assert evidence[0].result == "clear"

    def test_no_urls_is_clear(self):
        evidence = check_url_shortener([])
        assert evidence[0].result == "clear"


class TestIpLiteralUrl:
    def test_ipv4_literal_is_suspicious(self):
        evidence = check_ip_literal_url(["http://192.168.1.1/login"])
        assert evidence[0].result == "suspicious"

    def test_ipv6_literal_is_suspicious(self):
        evidence = check_ip_literal_url(["http://[2001:db8::1]/login"])
        assert evidence[0].result == "suspicious"

    def test_domain_url_is_clear(self):
        evidence = check_ip_literal_url(["https://bancoreal.com/login"])
        assert evidence[0].result == "clear"


class TestSenderMismatch:
    def test_no_claimed_org_is_clear(self):
        message = ExtractedMessage()
        evidence = check_sender_mismatch(message, [BANK])
        assert evidence[0].result == "clear"

    def test_org_not_in_trusted_circle_is_clear(self):
        message = ExtractedMessage(claimed_org="Some Other Bank")
        evidence = check_sender_mismatch(message, [BANK])
        assert evidence[0].result == "clear"

    def test_matching_contact_is_clear(self):
        message = ExtractedMessage(claimed_org="Banco Real", phones=["555-100-2000"])
        evidence = check_sender_mismatch(message, [BANK])
        assert evidence[0].result == "clear"

    def test_mismatched_contact_is_suspicious(self):
        message = ExtractedMessage(claimed_org="Banco Real", phones=["+1 900 555 0000"])
        evidence = check_sender_mismatch(message, [BANK])
        assert evidence[0].result == "suspicious"

    def test_no_sender_contact_extracted_is_clear(self):
        message = ExtractedMessage(claimed_org="Banco Real")
        evidence = check_sender_mismatch(message, [BANK])
        assert evidence[0].result == "clear"


class TestPaymentMethodChecks:
    def test_otp_request_is_severe(self):
        message = ExtractedMessage(payment_methods_requested=["otp_code"])
        evidence = run_checks(message, [])
        assert _results(evidence, "otp_request") == ["severe"]

    def test_gift_card_request_is_severe(self):
        message = ExtractedMessage(payment_methods_requested=["gift_card"])
        evidence = run_checks(message, [])
        assert _results(evidence, "gift_card_request") == ["severe"]

    def test_crypto_request_is_severe(self):
        message = ExtractedMessage(payment_methods_requested=["cryptocurrency"])
        evidence = run_checks(message, [])
        assert _results(evidence, "crypto_request") == ["severe"]

    def test_urgent_transfer_is_suspicious(self):
        message = ExtractedMessage(
            payment_methods_requested=["bank_transfer"], pressure_signals=["urgency"]
        )
        evidence = run_checks(message, [])
        assert _results(evidence, "urgent_transfer_request") == ["suspicious"]

    def test_transfer_without_urgency_is_clear(self):
        message = ExtractedMessage(payment_methods_requested=["bank_transfer"])
        evidence = run_checks(message, [])
        assert _results(evidence, "urgent_transfer_request") == ["clear"]

    def test_no_payment_signals_are_all_clear(self):
        message = ExtractedMessage()
        evidence = run_checks(message, [])
        for evidence_type in (
            "otp_request",
            "gift_card_request",
            "crypto_request",
            "urgent_transfer_request",
        ):
            assert _results(evidence, evidence_type) == ["clear"]


class TestRunChecks:
    def test_ids_are_sequential_and_unique(self):
        message = ExtractedMessage(payment_methods_requested=["otp_code"])
        evidence = run_checks(message, [BANK])
        ids = [e.id for e in evidence]
        assert ids == [f"chk-{i}" for i in range(1, len(evidence) + 1)]
        assert len(set(ids)) == len(ids)

    def test_clean_message_has_no_severe_or_suspicious_findings(self):
        message = ExtractedMessage(
            domains=["bancoreal.com"], phones=["555-100-2000"], claimed_org="Banco Real"
        )
        evidence = run_checks(message, [BANK])
        assert all(e.result == "clear" for e in evidence)
        assert floors_risk_high(evidence) is False


class TestFloorsRiskHigh:
    def test_true_when_any_severe(self):
        message = ExtractedMessage(payment_methods_requested=["gift_card"])
        evidence = run_checks(message, [])
        assert floors_risk_high(evidence) is True

    def test_false_when_only_suspicious_or_clear(self):
        message = ExtractedMessage(urls=["https://bit.ly/abc"])
        evidence = run_checks(message, [])
        assert floors_risk_high(evidence) is False
