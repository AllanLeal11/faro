"""Family alerts via Amazon SES (CLAUDE.md section 4 + AWS Builder mini
challenge).

The alert email deliberately contains NO message content (privacy, section 5):
only the risk level and a suggested verification question, plus a nudge to
confirm through an official channel.

Security:
- Header injection: CR/LF are stripped from the recipient and never allowed
  into the subject (CLAUDE.md 12.5, email injection).
- The body is plain text and a minimal escaped HTML part; no user-controlled
  HTML is interpolated.
- In MOCK_MODE no email is sent; the call is logged and reported as sent so
  the demo flows end-to-end without AWS.
- IAM: the credentials used here should be scoped to ses:SendEmail only
  (CLAUDE.md 12.1).
"""

from __future__ import annotations

import asyncio
import html
import logging

from app.config import Settings

logger = logging.getLogger("faro")

_CONNECT_TIMEOUT = 5.0
_READ_TIMEOUT = 15.0


def _sanitize_header(value: str) -> str:
    """Remove CR/LF and trim, to prevent header injection."""
    return value.replace("\r", "").replace("\n", "").strip()


def _compose(
    risk_level: str, verification_question: str, language: str, frontend_url: str
) -> tuple[str, str, str]:
    """Return (subject, text_body, html_body), all free of message content."""
    is_es = language.lower().startswith("es")
    question = verification_question.strip()

    if is_es:
        subject = "Faro: alguien cercano necesita ayuda para verificar un mensaje"
        lines = [
            "Hola,",
            "",
            "Un familiar usó Faro para revisar un mensaje y el resultado fue "
            f"riesgo {risk_level.upper()}.",
            "",
            "Puede ayudarle a confirmar antes de que haga nada.",
        ]
        if question:
            lines += ["", f"Pregunta sugerida para verificar: {question}"]
        lines += [
            "",
            "Importante: confirmen siempre llamando a la entidad por su número "
            "oficial, no por los datos del mensaje.",
        ]
    else:
        subject = "Faro: someone close to you needs help checking a message"
        lines = [
            "Hello,",
            "",
            "A family member used Faro to check a message and the result was "
            f"{risk_level.upper()} risk.",
            "",
            "You can help them confirm before they do anything.",
        ]
        if question:
            lines += ["", f"Suggested question to verify: {question}"]
        lines += [
            "",
            "Important: always confirm by calling the organization at its "
            "official number, not the contact details in the message.",
        ]

    text_body = "\n".join(lines)
    html_body = (
        '<html><body style="font-family:sans-serif;font-size:16px;'
        'line-height:1.5">'
        + "".join(f"<p>{html.escape(line)}</p>" for line in lines if line)
        + "</body></html>"
    )
    return subject, text_body, html_body


def _send_via_ses(
    settings: Settings, *, to_email: str, subject: str, text_body: str, html_body: str
) -> bool:
    import boto3
    from botocore.config import Config

    client = boto3.client(
        "ses",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(
            connect_timeout=_CONNECT_TIMEOUT,
            read_timeout=_READ_TIMEOUT,
            retries={"max_attempts": 2, "mode": "standard"},
        ),
    )
    client.send_email(
        Source=settings.ses_from_email,
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": text_body, "Charset": "UTF-8"},
                "Html": {"Data": html_body, "Charset": "UTF-8"},
            },
        },
    )
    return True


async def send_family_alert(
    settings: Settings,
    *,
    to_email: str,
    risk_level: str,
    verification_question: str,
    language: str,
) -> bool:
    """Send a family alert email. Returns True on success, False on failure.

    In MOCK_MODE, or when SES is not configured (no AWS credentials / verified
    sender), nothing is sent: the call is logged and reported as sent so the
    family-alert flow still demos end to end without AWS.
    """
    to_email = _sanitize_header(to_email)
    subject, text_body, html_body = _compose(
        risk_level, verification_question, language, settings.frontend_url
    )
    subject = _sanitize_header(subject)

    if settings.mock_mode or not settings.ses_configured:
        logger.info("Family alert (risk=%s) simulated — SES not configured.", risk_level)
        return True

    try:
        return await asyncio.to_thread(
            _send_via_ses,
            settings,
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
    except Exception as exc:  # noqa: BLE001 — SES/network errors
        logger.warning("SES send failed: %s", type(exc).__name__)
        return False
