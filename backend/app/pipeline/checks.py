"""Deterministic scam checks — the security floor, no LLM involved.

This stage is the backbone of Faro's trust model (CLAUDE.md sections 4 and
12.7): everything here is plain, auditable Python. If a severe signal fires
(lookalike domain, request for a one-time code/credentials, or a gift-card /
crypto / urgent-transfer demand), the downstream LLM verdict is NOT allowed
to lower the risk below "high". The model can add nuance; it can never
overrule the floor.

Design constraints:
- All regexes are length-bounded and free of nested quantifiers, so they
  run in linear time on adversarial input (CLAUDE.md 12.5, ReDoS).
- Text is NFKC-normalized before matching, and homoglyphs / punycode /
  bidi-control characters are detected explicitly (CLAUDE.md 12.5, Unicode).
- Faro never visits or resolves any URL; it only inspects the text of the
  URL and compares it to the trusted circle (CLAUDE.md 4 and 12.6).
- Nothing here logs or returns the raw message; callers handle display.
"""

from __future__ import annotations

import ipaddress
import re
import unicodedata

from app.pipeline.schemas import ChecksOutput, EvidenceItem, TrustedEntity

# --- Bounded IOC patterns -------------------------------------------------
# Each pattern caps its repetition count so a crafted input can't trigger
# catastrophic backtracking. Character classes are non-overlapping.

_URL_RE = re.compile(r"\bhttps?://[^\s<>\"']{1,2000}", re.IGNORECASE)
# Bare host like "banco-falso.com" or "pagos.sinpe.fi.cr". Labels are 1–63
# chars; the TLD is alphabetic. Linear-time (no nested quantifiers).
_DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.){1,8}[a-z]{2,24}\b",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(
    r"\b[a-z0-9._%+\-]{1,64}@([a-z0-9.\-]{1,255}\.[a-z]{2,24})\b",
    re.IGNORECASE,
)
# Phone-ish run of digits with common separators, 7–20 glyphs total.
_PHONE_RE = re.compile(r"(?<![\w])\+?\d[\d\s\-().]{5,18}\d(?![\w])")

# --- Known URL shorteners -------------------------------------------------
_SHORTENERS = frozenset(
    {
        "bit.ly",
        "tinyurl.com",
        "goo.gl",
        "t.co",
        "ow.ly",
        "is.gd",
        "buff.ly",
        "rebrand.ly",
        "cutt.ly",
        "shorturl.at",
        "rb.gy",
        "t.ly",
        "acortar.link",
        "bl.ink",
        "lnkd.in",
        "s.id",
        "v.gd",
    }
)

# --- Confusable (homoglyph) map: common non-ASCII look-alikes to ASCII ----
# Focused on the characters actually used in domain-spoofing: Cyrillic and
# Greek letters that render like Latin ones, plus a few full-width forms.
_CONFUSABLES = {
    # Cyrillic look-alikes
    chr(0x0430): "a",
    chr(0x0435): "e",
    chr(0x043E): "o",
    chr(0x0440): "p",
    chr(0x0441): "c",
    chr(0x0443): "y",
    chr(0x0445): "x",
    chr(0x0456): "i",
    chr(0x0455): "s",
    chr(0x0458): "j",
    chr(0x04BB): "h",
    chr(0x0501): "d",
    chr(0x043D): "h",
    chr(0x043A): "k",
    chr(0x043C): "m",
    chr(0x0442): "t",
    chr(0x0432): "b",
    chr(0x0433): "r",
    # Greek look-alikes
    chr(0x03BF): "o",
    chr(0x03B1): "a",
    chr(0x03BD): "v",
    chr(0x03B9): "i",
    chr(0x03C1): "p",
    chr(0x03C5): "u",
    chr(0x03BA): "k",
    chr(0x03C4): "t",
    # Full-width / dot look-alikes
    chr(0xFF41): "a",
    chr(0xFF4F): "o",
    chr(0x0251): "a",
    chr(0x2024): ".",
    chr(0x3002): ".",
    chr(0xFF0E): ".",
}

# Bidirectional and invisible control characters used to disguise text.
_BIDI_CONTROLS = frozenset(
    chr(cp)
    for cp in (
        0x202A,
        0x202B,
        0x202C,
        0x202D,
        0x202E,  # LRE/RLE/PDF/LRO/RLO
        0x2066,
        0x2067,
        0x2068,
        0x2069,  # LRI/RLI/FSI/PDI
        0x200E,
        0x200F,
        0x061C,  # LRM/RLM/ALM
        0x200B,
        0x200C,
        0x200D,
        0xFEFF,  # zero-width family
    )
)

# --- Keyword signals (Spanish + English) ----------------------------------
# Lowercased, accent-insensitive matching (see _fold). These are substrings,
# not regexes, so there is no backtracking risk.
_OTP_TERMS = (
    "codigo de verificacion",
    "codigo de seguridad",
    "codigo sinpe",
    "codigo otp",
    "clave temporal",
    "clave dinamica",
    "no comparta este codigo",
    "no comparta el codigo",
    "verification code",
    "security code",
    "one-time code",
    "one time code",
    "otp",
    "two-factor",
    "codigo de un solo uso",
)
_CREDENTIAL_TERMS = (
    "contrasena",
    "clave de acceso",
    "usuario y clave",
    "numero de tarjeta",
    "cvv",
    "codigo de la tarjeta",
    "pin de su tarjeta",
    "datos de su cuenta",
    "password",
    "card number",
    "account number",
    "login",
    "credenciales",
)
_GIFTCARD_CRYPTO_TERMS = (
    "tarjeta de regalo",
    "gift card",
    "giftcard",
    "itunes",
    "google play",
    "steam",
    "bitcoin",
    "btc",
    "usdt",
    "ethereum",
    "cripto",
    "crypto",
    "criptomoneda",
    "billetera",
    "wallet",
    "transferencia urgente",
    "wire transfer",
    "sinpe movil urgente",
    "deposito inmediato",
)
_URGENCY_TERMS = (
    "urgente",
    "inmediatamente",
    "ahora mismo",
    "su cuenta sera bloqueada",
    "su cuenta ha sido bloqueada",
    "ultimo aviso",
    "en las proximas",
    "expira hoy",
    "accion requerida",
    "urgent",
    "immediately",
    "act now",
    "account will be suspended",
    "final notice",
    "suspended",
)


def _fold(text: str) -> str:
    """Lowercase and strip accents for keyword matching (not for display)."""
    decomposed = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return no_accents.lower()


def normalize(text: str) -> str:
    """NFKC-normalize and remove bidi/zero-width controls.

    Used as the canonical form for analysis. Display-side defanging is
    separate (see `defang`).
    """
    cleaned = "".join(c for c in text if c not in _BIDI_CONTROLS)
    return unicodedata.normalize("NFKC", cleaned)


def _deconfuse(label: str) -> str:
    """Map known confusable characters in a domain label to their ASCII twin."""
    return "".join(_CONFUSABLES.get(c, c) for c in label)


def defang(url_or_domain: str) -> str:
    """Render a hostile URL/domain safe to display as plain text.

    e.g. "https://banco-falso.com/x" -> "hxxps://banco-falso[.]com/x".
    Never produces a clickable link (CLAUDE.md 12.5, XSS).
    """
    out = url_or_domain.replace("http", "hxxp").replace(".", "[.]")
    return out


def _host_of(url: str) -> str:
    """Extract the host from a URL's text without resolving it."""
    # Strip scheme.
    rest = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
    # Host ends at the first /, ?, #, or whitespace.
    host = re.split(r"[/?#\s]", rest, maxsplit=1)[0]
    # Drop userinfo and port.
    host = host.split("@")[-1].split(":")[0]
    return host.strip(".").lower()


def _levenshtein(a: str, b: str, *, cap: int = 3) -> int:
    """Bounded Levenshtein distance; returns `cap + 1` once it exceeds cap."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        best = i
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            val = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
            curr.append(val)
            best = min(best, val)
        if best > cap:
            return cap + 1
        prev = curr
    return prev[-1]


def _registrable(host: str) -> str:
    """Best-effort registrable domain (last two labels).

    Not a full public-suffix implementation — good enough to compare a found
    host against a trusted domain. Multi-label ccTLDs (e.g. "fi.cr") are
    handled for the Costa Rican cases Faro cares about.
    """
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    # Handle a small set of known second-level public suffixes.
    two = ".".join(labels[-2:])
    known_sld = {"fi.cr", "co.cr", "or.cr", "go.cr", "ac.cr", "co.uk", "com.mx"}
    if two in known_sld and len(labels) >= 3:
        return ".".join(labels[-3:])
    return two


def _iter_terms(folded: str, terms: tuple[str, ...]) -> list[str]:
    return [t for t in terms if t in folded]


def run_checks(message: str, trusted: list[TrustedEntity]) -> ChecksOutput:
    """Run every deterministic check and return evidence + a severity floor.

    Args:
        message: the raw suspicious text (as pasted by the user).
        trusted: the user's trusted circle (banks, companies, contacts).

    Returns:
        ChecksOutput with evidence items, a `severe_hit` flag, and the
        defanged forms of all URLs for safe display.
    """
    norm = normalize(message)
    folded = _fold(norm)
    evidence: list[EvidenceItem] = []
    severe = False
    counter = 0

    def add(
        type_: str,
        result: str,
        detail: str,
        *,
        is_severe: bool = False,
        source_url: str | None = None,
    ) -> None:
        nonlocal counter, severe
        counter += 1
        evidence.append(
            EvidenceItem(
                id=f"chk-{counter}",
                kind="check",
                type=type_,
                result=result,
                detail=detail,
                source_url=source_url,
                severe=is_severe,
            )
        )
        if is_severe:
            severe = True

    # --- Collect IOCs from the text (deterministic, no LLM) ---
    urls = _URL_RE.findall(norm)
    hosts = [_host_of(u) for u in urls]
    bare_domains = [d.lower() for d in _DOMAIN_RE.findall(norm)]
    email_domains = [m.lower() for m in _EMAIL_RE.findall(norm)]
    all_hosts = list(dict.fromkeys(h for h in [*hosts, *bare_domains, *email_domains] if h))
    defanged = [defang(u) for u in urls] + [
        defang(d) for d in bare_domains if d not in {_host_of(u) for u in urls}
    ]

    # Flatten trusted domains for comparison.
    trusted_domains = {_registrable(d.lower()) for e in trusted for d in e.domains if d}
    trusted_brand_tokens = {
        tok for e in trusted for tok in _fold(e.name).replace("-", " ").split() if len(tok) >= 3
    }

    # --- Check: bidi / zero-width disguise ---
    if any(c in _BIDI_CONTROLS for c in message):
        add(
            "bidi_trick",
            "hit",
            "The message hides text direction or invisible characters, a "
            "technique used to disguise links or senders.",
        )

    # --- Per-host checks: punycode, homoglyph, shortener, IP, lookalike ---
    for host in all_hosts:
        reg = _registrable(host)

        # Punycode / IDN homograph.
        if "xn--" in host:
            add(
                "punycode_domain",
                "hit",
                f"The address {defang(host)} uses punycode, which can hide a look-alike domain.",
                is_severe=True,
            )
        # Raw non-ASCII letters in a host (homoglyph attack).
        elif any(ord(c) > 127 for c in host):
            ascii_form = _deconfuse(host)
            add(
                "homoglyph_domain",
                "hit",
                f"The address {defang(host)} mixes look-alike characters from "
                f"another alphabet (reads like {defang(ascii_form)}).",
                is_severe=True,
            )

        # IP-literal host.
        try:
            ipaddress.ip_address(host)
            add(
                "ip_url",
                "hit",
                f"The link points to a raw IP address ({defang(host)}) instead "
                "of a named website — legitimate banks don't do this.",
            )
        except ValueError:
            pass

        # URL shortener.
        if reg in _SHORTENERS:
            add(
                "url_shortener",
                "hit",
                f"The link uses a shortener ({defang(reg)}) that hides the real destination.",
            )

        # Look-alike of a trusted domain (edit distance on the deconfused form).
        deconfused_reg = _deconfuse(reg)
        for td in trusted_domains:
            if deconfused_reg == td:
                continue
            dist = _levenshtein(deconfused_reg, td, cap=2)
            if 0 < dist <= 2:
                add(
                    "lookalike_domain",
                    "hit",
                    f"The address {defang(reg)} is a near-copy of your trusted "
                    f"site {defang(td)} (off by {dist} character"
                    f"{'s' if dist != 1 else ''}).",
                    is_severe=True,
                )
                break

        # Brand token present but domain is not the official one.
        host_tokens = set(_fold(reg).replace(".", " ").replace("-", " ").split())
        shared = host_tokens & trusted_brand_tokens
        if shared and reg not in trusted_domains:
            add(
                "sender_mismatch",
                "hit",
                f"The address {defang(reg)} uses your trusted brand name "
                f"({', '.join(sorted(shared))}) but is not its official site.",
                is_severe=True,
            )

    # --- Keyword-based intent checks ---
    if _iter_terms(folded, _OTP_TERMS):
        add(
            "otp_request",
            "hit",
            "The message asks for a one-time / verification code. Real banks "
            "never ask you to share these.",
            is_severe=True,
        )
    if _iter_terms(folded, _CREDENTIAL_TERMS):
        add(
            "credential_request",
            "hit",
            "The message asks for passwords, card numbers or account details.",
            is_severe=True,
        )
    if _iter_terms(folded, _GIFTCARD_CRYPTO_TERMS):
        add(
            "giftcard_or_crypto",
            "hit",
            "The message pushes payment via gift cards, crypto or an urgent "
            "transfer — a hallmark of scams.",
            is_severe=True,
        )
    urgency = _iter_terms(folded, _URGENCY_TERMS)
    if urgency:
        add(
            "urgency_pressure",
            "hit",
            "The message uses pressure and urgency to rush you into acting.",
        )

    return ChecksOutput(evidence=evidence, severe_hit=severe, defanged_urls=defanged)
