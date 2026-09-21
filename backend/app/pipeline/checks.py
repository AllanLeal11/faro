"""Deterministic checks — no LLM call in this module (CLAUDE.md section 4.2).

Each `check_*` function inspects the facts extract.py already pulled out of
the message (never the raw text) against the user's trusted circle and
returns one `Evidence` item per finding, or a single "clear" item when the
check ran and found nothing. `run_checks` runs all of them in a fixed order
and assigns each item a stable id that verdict.py can later cite.

Any domain or URL taken from the analyzed message is defanged before it
goes into an evidence `detail` (CLAUDE.md section 12.5): never a live,
clickable link, and safe to read aloud in the voice simulation.
"""

import ipaddress
import re
import unicodedata
from urllib.parse import urlsplit

from app.pipeline.schemas import Evidence, EvidenceResult, ExtractedMessage, TrustedEntity

MAX_DOMAIN_LEN = 253

SHORTENER_DOMAINS = frozenset(
    {
        "bit.ly",
        "tinyurl.com",
        "t.co",
        "goo.gl",
        "ow.ly",
        "is.gd",
        "buff.ly",
        "rebrand.ly",
        "cutt.ly",
        "tiny.cc",
        "rb.gy",
        "shorturl.at",
        "bl.ink",
        "lnkd.in",
        "tr.im",
        "v.gd",
        "s.id",
        "short.io",
        "clck.ru",
        "qr.ae",
    }
)

# Single-character confusables mapped to their canonical ASCII letter, used
# to build a comparable "skeleton" of a domain (Cyrillic/Greek lookalikes
# plus common leetspeak digit substitutions). Not exhaustive — a defense
# layer, not a guarantee.
_CONFUSABLES = {
    "0": "o",
    "1": "l",
    "3": "e",
    "5": "s",
    "8": "b",
    "а": "a",  # CYRILLIC SMALL LETTER A
    "е": "e",  # CYRILLIC SMALL LETTER IE
    "о": "o",  # CYRILLIC SMALL LETTER O
    "р": "p",  # CYRILLIC SMALL LETTER ER
    "с": "c",  # CYRILLIC SMALL LETTER ES
    "у": "y",  # CYRILLIC SMALL LETTER U
    "х": "x",  # CYRILLIC SMALL LETTER HA
    "і": "i",  # CYRILLIC SMALL LETTER BYELORUSSIAN-UKRAINIAN I
    "ѕ": "s",  # CYRILLIC SMALL LETTER DZE
    "ј": "j",  # CYRILLIC SMALL LETTER JE
    "ο": "o",  # GREEK SMALL LETTER OMICRON
    "ν": "v",  # GREEK SMALL LETTER NU
    "Α": "a",  # GREEK CAPITAL LETTER ALPHA (rare, defensive)
}

_NON_DIGITS = re.compile(r"\D")


def _evidence_id(index: int) -> str:
    return f"chk-{index}"


def _defang(value: str) -> str:
    """Neutralize a URL/domain so it can never render as a clickable link."""
    return value.replace("http://", "hxxp://").replace("https://", "hxxps://").replace(".", "[.]")


def _normalize_domain(domain: str) -> str:
    return unicodedata.normalize("NFKC", domain).strip().strip(".").lower()


def _decode_punycode_domain(domain: str) -> str:
    """Best-effort punycode decode, label by label. Falls back to the input
    unchanged for anything that isn't valid punycode."""
    decoded_labels = []
    for label in domain.split("."):
        if label.startswith("xn--"):
            try:
                decoded_labels.append(label[4:].encode("ascii").decode("punycode"))
                continue
            except (UnicodeError, ValueError):
                pass
        decoded_labels.append(label)
    return ".".join(decoded_labels)


def _script_of(char: str) -> str | None:
    code_point = ord(char)
    is_basic_latin = 0x0041 <= code_point <= 0x005A or 0x0061 <= code_point <= 0x007A
    is_latin_extended = 0x00C0 <= code_point <= 0x024F
    if is_basic_latin or is_latin_extended:
        return "latin"
    if 0x0370 <= code_point <= 0x03FF:
        return "greek"
    if 0x0400 <= code_point <= 0x04FF:
        return "cyrillic"
    return None


def _is_mixed_script(domain: str) -> bool:
    scripts = {script for char in domain if (script := _script_of(char)) is not None}
    return len(scripts) > 1


def _skeletonize(domain: str) -> str:
    return "".join(_CONFUSABLES.get(char, char) for char in domain)


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current_row = [i] + [0] * len(b)
        for j, char_b in enumerate(b, start=1):
            current_row[j] = min(
                current_row[j - 1] + 1,  # insertion
                previous_row[j] + 1,  # deletion
                previous_row[j - 1] + (char_a != char_b),  # substitution
            )
        previous_row = current_row
    return previous_row[-1]


def _extract_host(url: str) -> str | None:
    candidate = url if "://" in url else f"//{url}"
    try:
        return urlsplit(candidate).hostname
    except ValueError:
        return None


def _phone_key(phone: str) -> str:
    """Digits-only, last 10, so a national number matches its +country form."""
    digits = _NON_DIGITS.sub("", phone)
    return digits[-10:] if len(digits) >= 10 else digits


def check_domain_lookalike(
    domains: list[str], trusted_entities: list[TrustedEntity]
) -> list[Evidence]:
    trusted_domains = {_normalize_domain(d) for entity in trusted_entities for d in entity.domains}
    findings: list[tuple[EvidenceResult, str]] = []

    for raw_domain in domains:
        if not raw_domain or len(raw_domain) > MAX_DOMAIN_LEN:
            continue

        normalized = _normalize_domain(raw_domain)
        if normalized in trusted_domains:
            continue  # exact match to a trusted domain: nothing to flag

        display = _defang(raw_domain)
        decoded = _decode_punycode_domain(normalized)
        has_punycode = decoded != normalized
        skeleton = _skeletonize(decoded)

        best_match: str | None = None
        best_distance: int | None = None
        for trusted in trusted_domains:
            distance = _levenshtein(skeleton, _skeletonize(trusted))
            if best_distance is None or distance < best_distance:
                best_distance, best_match = distance, trusted

        if best_match is not None and skeleton == _skeletonize(best_match):
            findings.append(
                (
                    "severe",
                    f"{display} looks identical to the trusted domain {best_match} but is "
                    "made of different characters (possible homoglyph impersonation).",
                )
            )
            continue

        is_close_variant = (
            best_match is not None
            and best_distance is not None
            and len(best_match) > 3
            and 0 < best_distance <= 2
        )
        if is_close_variant:
            findings.append(
                (
                    "severe",
                    f"{display} closely resembles the trusted domain {best_match} "
                    f"(edit distance {best_distance}); this looks like typosquatting.",
                )
            )
            continue

        if has_punycode:
            findings.append(
                (
                    "suspicious",
                    f"{display} uses internationalized (punycode) encoding, which is "
                    "sometimes used to disguise lookalike domains.",
                )
            )
            continue

        if _is_mixed_script(decoded):
            findings.append(
                (
                    "suspicious",
                    f"{display} mixes letters from different alphabets in one domain "
                    "name, a common spoofing technique.",
                )
            )

    if not findings:
        return [
            Evidence(
                id="",
                type="domain_lookalike",
                result="clear",
                detail="No domain in the message resembles a trusted entity or shows "
                "signs of spoofing.",
            )
        ]
    return [
        Evidence(id="", type="domain_lookalike", result=result, detail=detail)
        for result, detail in findings
    ]


def check_url_shortener(urls: list[str]) -> list[Evidence]:
    findings = []
    for url in urls:
        host = _extract_host(url)
        if host and _normalize_domain(host) in SHORTENER_DOMAINS:
            findings.append(
                Evidence(
                    id="",
                    type="url_shortener",
                    result="suspicious",
                    detail=f"{_defang(url)} uses a link-shortening service, which can "
                    "hide the real destination of the link.",
                )
            )
    if not findings:
        return [
            Evidence(
                id="",
                type="url_shortener",
                result="clear",
                detail="No link-shortening service was found in the message's URLs.",
            )
        ]
    return findings


def check_ip_literal_url(urls: list[str]) -> list[Evidence]:
    findings = []
    for url in urls:
        host = _extract_host(url)
        if not host:
            continue
        try:
            ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            continue
        findings.append(
            Evidence(
                id="",
                type="ip_literal_url",
                result="suspicious",
                detail=f"{_defang(url)} points directly to an IP address instead of a "
                "domain name, which is unusual for a legitimate sender.",
            )
        )
    if not findings:
        return [
            Evidence(
                id="",
                type="ip_literal_url",
                result="clear",
                detail="No URL in the message points directly to an IP address.",
            )
        ]
    return findings


def check_sender_mismatch(
    message: ExtractedMessage, trusted_entities: list[TrustedEntity]
) -> list[Evidence]:
    if not message.claimed_org:
        return [
            Evidence(
                id="",
                type="sender_mismatch",
                result="clear",
                detail="No sender organization was identified in the message.",
            )
        ]

    claimed_normalized = message.claimed_org.strip().lower()
    matching_entity = next(
        (e for e in trusted_entities if e.name.strip().lower() == claimed_normalized), None
    )
    if matching_entity is None:
        return [
            Evidence(
                id="",
                type="sender_mismatch",
                result="clear",
                detail=f"'{message.claimed_org}' is not in the user's trusted circle, so "
                "there is nothing on file to compare it against.",
            )
        ]

    if not message.phones and not message.emails:
        return [
            Evidence(
                id="",
                type="sender_mismatch",
                result="clear",
                detail=f"No sender phone number or email was found in the message to "
                f"compare with {matching_entity.name}'s records.",
            )
        ]

    known_contacts = {_phone_key(p) for p in matching_entity.phones} | {
        e.strip().lower() for e in matching_entity.emails
    }
    message_contacts = {_phone_key(p) for p in message.phones} | {
        e.strip().lower() for e in message.emails
    }

    if message_contacts & known_contacts:
        return [
            Evidence(
                id="",
                type="sender_mismatch",
                result="clear",
                detail=f"The sender's contact information matches {matching_entity.name}'s "
                "records on file.",
            )
        ]

    return [
        Evidence(
            id="",
            type="sender_mismatch",
            result="suspicious",
            detail=f"The message claims to be from {matching_entity.name}, but the "
            "sender's phone number or email does not match the official contact "
            "information on file.",
        )
    ]


def check_otp_request(message: ExtractedMessage) -> list[Evidence]:
    if "otp_code" in message.payment_methods_requested:
        return [
            Evidence(
                id="",
                type="otp_request",
                result="severe",
                detail="The message asks for a one-time verification code. Legitimate "
                "banks and companies never ask for this.",
            )
        ]
    return [
        Evidence(
            id="",
            type="otp_request",
            result="clear",
            detail="The message does not ask for a one-time verification code.",
        )
    ]


def check_gift_card_request(message: ExtractedMessage) -> list[Evidence]:
    if "gift_card" in message.payment_methods_requested:
        return [
            Evidence(
                id="",
                type="gift_card_request",
                result="severe",
                detail="The message asks for payment in gift cards, a payment method "
                "almost never used by legitimate organizations and heavily favored by "
                "scammers.",
            )
        ]
    return [
        Evidence(
            id="",
            type="gift_card_request",
            result="clear",
            detail="The message does not ask for payment in gift cards.",
        )
    ]


def check_crypto_request(message: ExtractedMessage) -> list[Evidence]:
    if "cryptocurrency" in message.payment_methods_requested:
        return [
            Evidence(
                id="",
                type="crypto_request",
                result="severe",
                detail="The message asks for payment in cryptocurrency, a payment "
                "method almost never used by legitimate organizations and heavily "
                "favored by scammers.",
            )
        ]
    return [
        Evidence(
            id="",
            type="crypto_request",
            result="clear",
            detail="The message does not ask for payment in cryptocurrency.",
        )
    ]


def check_urgent_transfer_request(message: ExtractedMessage) -> list[Evidence]:
    wants_transfer = "bank_transfer" in message.payment_methods_requested
    is_urgent = "urgency" in message.pressure_signals
    if wants_transfer and is_urgent:
        return [
            Evidence(
                id="",
                type="urgent_transfer_request",
                result="suspicious",
                detail="The message pressures the reader to make an urgent bank "
                "transfer, a common pattern in scams.",
            )
        ]
    return [
        Evidence(
            id="",
            type="urgent_transfer_request",
            result="clear",
            detail="The message does not combine a bank transfer request with urgent pressure.",
        )
    ]


def run_checks(message: ExtractedMessage, trusted_entities: list[TrustedEntity]) -> list[Evidence]:
    """Run every deterministic check and return one flat, id-assigned list."""
    evidence = [
        *check_domain_lookalike(message.domains, trusted_entities),
        *check_url_shortener(message.urls),
        *check_ip_literal_url(message.urls),
        *check_sender_mismatch(message, trusted_entities),
        *check_otp_request(message),
        *check_gift_card_request(message),
        *check_crypto_request(message),
        *check_urgent_transfer_request(message),
    ]
    return [
        item.model_copy(update={"id": _evidence_id(i)}) for i, item in enumerate(evidence, start=1)
    ]


def floors_risk_high(evidence: list[Evidence]) -> bool:
    """CLAUDE.md section 12.7: a severe deterministic finding sets a floor —
    verdict.py must not report a risk level below "high" when this is True.
    """
    return any(item.result == "severe" for item in evidence)
