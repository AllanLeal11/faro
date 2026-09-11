"""Security headers and request-size limit middleware (CLAUDE.md section 12.2).

Two independent, composable pieces:

- SecurityHeadersMiddleware: sets a strict CSP and the other required
  headers on every response. The only CSP exception is Swagger's own
  assets on /docs, and only when ENVIRONMENT=development — in production
  /docs is disabled entirely (see main.py), so the exception is dead code
  there, not a live hole.
- BodySizeLimitMiddleware: rejects oversized request bodies with 413
  before they reach any route. This is a coarse, whole-request safety net;
  the 5,000-character message limit from section 12.5 is enforced
  separately, on the message field itself, in the pipeline (block 3).
"""

from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp

# Generous enough for a /api/check payload (5,000-char message plus a
# trusted-circle snapshot and metadata) while still ruling out abuse.
MAX_BODY_BYTES = 256 * 1024

_STRICT_CSP = "; ".join(
    [
        "default-src 'none'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "form-action 'self'",
    ]
)

# Swagger UI (served at /docs) loads its own inline script and CDN assets.
# Only reachable when ENVIRONMENT=development, since /docs itself is
# disabled otherwise (see main.py) — this is not a production exception.
_DOCS_DEV_CSP = "; ".join(
    [
        "default-src 'none'",
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "img-src 'self' data: https://fastapi.tiangolo.com",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
    ]
)


class SecurityHeadersMiddleware:
    """Pure ASGI middleware: sets security headers on every response."""

    def __init__(self, app: ASGIApp, *, is_production: bool, is_development: bool) -> None:
        self.app = app
        self.is_production = is_production
        self.is_development = is_development

    async def __call__(self, scope, receive, send) -> None:  # noqa: ANN001
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        is_docs_path = path.startswith(("/docs", "/redoc"))

        async def send_wrapper(message):  # noqa: ANN001
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                csp = _DOCS_DEV_CSP if (is_docs_path and self.is_development) else _STRICT_CSP
                headers.append((b"content-security-policy", csp.encode()))
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"x-frame-options", b"DENY"))
                headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))
                headers.append((b"permissions-policy", b"microphone=(self)"))
                if self.is_production:
                    headers.append(
                        (
                            b"strict-transport-security",
                            b"max-age=63072000; includeSubDomains",
                        )
                    )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)


class BodySizeLimitMiddleware:
    """Rejects requests whose declared Content-Length exceeds MAX_BODY_BYTES.

    Checked as pure ASGI (not BaseHTTPMiddleware) so it runs before Starlette
    reads the body, and can't be bypassed by a chunked request lying about
    its size — an oversized body without Content-Length is still cut off
    starlette's own limits before hitting a route.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:  # noqa: ANN001
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                length = None
            if length is not None and length > self.max_bytes:
                response = PlainTextResponse("Request body too large.", status_code=413)
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
