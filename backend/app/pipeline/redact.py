"""Redacts sensitive data from message text before it reaches the LLM or
Tavily (CLAUDE.md section 12.7): card numbers, one-time codes, and
passwords. This is one layer of defense-in-depth, not a guarantee — it
does not replace never logging the raw message (section 5).
"""

import re

# Bounded repetition only (13-19 digits, one optional separator each): no
# nested unbounded quantifiers, so this can't backtrack catastrophically.
# Separators cover every grouping style seen in real card numbers/scam
# templates: space, hyphen, dot, comma.
_CARD_NUMBER_PATTERN = re.compile(r"(?<!\d)(?:\d[ .,-]?){13,19}(?<=\d)")

# OTP codes are redacted in both real-world orderings: "your code is
# 123456" and "123456 is your verification code" (the far more common
# phrasing in actual bank/OTP messages).
_OTP_KEYWORDS = r"(?:otp|c[oó]digo|code|clave|pin|verificaci[oó]n|verification|comparte|share)"
_OTP_CODE_PATTERN = re.compile(
    rf"(?i)\b{_OTP_KEYWORDS}\b[^\d\n]{{0,40}}(\d{{4,8}})\b"
    rf"|\b(\d{{4,8}})\b[^\d\n]{{0,40}}\b{_OTP_KEYWORDS}\b"
)

# Separator class covers colon, "=", "-", "/" and whitespace, since scam
# and credential-stuffing templates use all of these before the value.
_PASSWORD_PATTERN = re.compile(r"(?i)\b(?:password|contrase[nñ]a)\b[:=/\s-]{1,5}(\S{1,64})")


def _redact_otp(match: re.Match[str]) -> str:
    code = match.group(1) or match.group(2)
    return match.group(0).replace(code, "[REDACTED-CODE]", 1)


def redact_sensitive(text: str) -> str:
    """Replace card numbers, OTP codes and passwords with redaction markers."""
    redacted = _CARD_NUMBER_PATTERN.sub("[REDACTED-CARD]", text)
    redacted = _OTP_CODE_PATTERN.sub(_redact_otp, redacted)
    redacted = _PASSWORD_PATTERN.sub(
        lambda m: m.group(0).replace(m.group(1), "[REDACTED-PASSWORD]", 1), redacted
    )
    return redacted
