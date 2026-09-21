"""Redacts sensitive data from message text before it reaches the LLM or
Tavily (CLAUDE.md section 12.7): card numbers, one-time codes, and
passwords. This is one layer of defense-in-depth, not a guarantee — it
does not replace never logging the raw message (section 5).
"""

import re

# Bounded repetition only (13-19 digits, one optional separator each): no
# nested unbounded quantifiers, so this can't backtrack catastrophically.
_CARD_NUMBER_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?<=\d)")

_OTP_CODE_PATTERN = re.compile(
    r"(?i)\b(?:otp|c[oó]digo|code|clave|pin)\b[^\d\n]{0,40}(\d{4,8})\b"
)

_PASSWORD_PATTERN = re.compile(
    r"(?i)\b(?:password|contrase[nñ]a)\b[:\s]{1,5}(\S{1,64})"
)


def redact_sensitive(text: str) -> str:
    """Replace card numbers, OTP codes and passwords with redaction markers."""
    redacted = _CARD_NUMBER_PATTERN.sub("[REDACTED-CARD]", text)
    redacted = _OTP_CODE_PATTERN.sub(
        lambda m: m.group(0).replace(m.group(1), "[REDACTED-CODE]", 1), redacted
    )
    redacted = _PASSWORD_PATTERN.sub(
        lambda m: m.group(0).replace(m.group(1), "[REDACTED-PASSWORD]", 1), redacted
    )
    return redacted
