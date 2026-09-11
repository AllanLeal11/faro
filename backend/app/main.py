"""Faro backend entrypoint.

CLAUDE.md section 12.10: no error tracebacks to the client, DEBUG off,
/docs disabled outside development, /health reveals nothing internal.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.middleware.security import BodySizeLimitMiddleware, SecurityHeadersMiddleware

logger = logging.getLogger("faro")

settings = get_settings()
_is_dev = settings.environment == "development"

app = FastAPI(
    title="Faro API",
    # /docs and /openapi.json only exist in development; in every other
    # environment FastAPI serves neither, so there is nothing to protect.
    docs_url="/docs" if _is_dev else None,
    redoc_url="/redoc" if _is_dev else None,
    openapi_url="/openapi.json" if _is_dev else None,
)

# Order matters: Starlette runs middleware in reverse of the order added,
# so the last one added here runs first on the request. We want the body
# size check to run before anything else touches the request, and the
# security headers to wrap every response including error responses —
# both achieved by adding them last.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,  # never combine "*" origins with credentials
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(
    SecurityHeadersMiddleware,
    is_production=settings.is_production,
    is_development=_is_dev,
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Pass through FastAPI/Starlette's own intentional HTTP errors (404,
    # 413, etc.) as-is — they don't leak internals.
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Pydantic validation errors describe the client's own malformed
    # request, not server internals, so they're safe to return as-is.
    return JSONResponse(status_code=422, content={"detail": "Invalid request."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Anything unexpected: log server-side with full detail, tell the
    # client nothing. Never include exc, a traceback, or request content
    # in the response — and never log the request body (may contain the
    # message being analyzed).
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/health")
async def health() -> dict:
    # Deliberately minimal: no version, no build info, no config echo.
    return {"status": "ok"}
