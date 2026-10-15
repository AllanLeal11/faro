"""Mask secrets before any message text leaves the backend.

CLAUDE.md section 12.7 ("datos sensibles"): before the message is sent to the
LLM or to Tavily, card numbers, one-time codes and passwords must be hidden.
The deterministic checks (checks.py) have already flagged *that* these appear;
the model only needs the structure, never the secret value.

These transforms are intentionally conservative — they protect the clearly
sensitive tokens while leaving enough of the message for the model to reason
about tone, sender and requested action.
"""

from __future__ import annotations

import re

# A card-like run: 13–19 digits, optionally separated by spaces or dashes.
# Bounded repetition; no nested quantifiers (anti-ReDoS, section 12.5).
_CARD_RE = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")

# A standalone numeric code of 4–8 digits (OTP / verification code).
_CODE_RE = re.compile(r"(?<!\d)\d{4,8}(?!\d)")

# A value following a password/clave label, up to the next whitespace.
_PASSWORD_RE = re.compile(r"(?i)\b(?:password|contrase[nñ]a|clave|pin)\b\s*[:=]?\s*(\S{1,64})")


def mask_secrets(text: str) -> str:
    """Return the message with cards, codes and passwords masked.

    - Card-like numbers keep only their last four digits.
    - Standalone 4–8 digit codes become a fixed placeholder.
    - A value after a password/clave/pin label is replaced.
    """

    # Card and password values are swapped for single-char sentinels first so
    # the later OTP-code pass can't clobber a card's preserved last four
    # digits. The sentinels (\x00 + index + \x00) contain no 4+ digit run, so
    # _CODE_RE leaves them alone; they are restored at the end.
    placeholders: dict[str, str] = {}

    def _stash(value: str) -> str:
        token = f"\x00{len(placeholders)}\x00"
        placeholders[token] = value
        return token

    def _mask_card(m: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        last4 = digits[-4:] if len(digits) >= 4 else ""
        return _stash(f"[card ending {last4}]")

    def _mask_password(m: re.Match[str]) -> str:
        return _stash(m.group(0).replace(m.group(1), "[secret]"))

    out = _CARD_RE.sub(_mask_card, text)
    out = _PASSWORD_RE.sub(_mask_password, out)
    out = _CODE_RE.sub("[code]", out)
    for token, value in placeholders.items():
        out = out.replace(token, value)
    return out
