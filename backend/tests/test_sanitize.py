"""Tests for secret masking before text leaves the backend (CLAUDE.md 12.7)."""

from __future__ import annotations

from app.pipeline.sanitize import mask_secrets


def test_card_number_keeps_only_last_four():
    out = mask_secrets("Mi tarjeta es 4512 8800 1234 5678 por favor")
    assert "4512 8800 1234 5678" not in out
    assert "5678" in out
    assert "[card ending 5678]" in out


def test_otp_code_is_masked():
    out = mask_secrets("Su codigo es 884120")
    assert "884120" not in out
    assert "[code]" in out


def test_password_value_is_masked():
    out = mask_secrets("password: Hunter2xyz")
    assert "Hunter2xyz" not in out
    assert "[secret]" in out


def test_ordinary_text_is_untouched():
    text = "Hola, nos vemos el martes a las 3."
    # The "3" is a single digit, not a code; nothing should be masked.
    assert mask_secrets(text) == text
