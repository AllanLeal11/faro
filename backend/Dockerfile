# Faro backend image — serves both the API and the MCP server (the start
# command selects which). Minimal base, non-root user (CLAUDE.md 12.11).
FROM python:3.13-slim

# uv for fast, locked installs.
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

RUN useradd --create-home --uid 10001 app
WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
RUN chown -R app:app /app
USER app

ENV PORT=8000
# Default: the REST API. The MCP service overrides CMD with:
#   uv run uvicorn app.mcp_server.asgi:app --host 0.0.0.0 --port $PORT
CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
