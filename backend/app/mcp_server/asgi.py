"""ASGI entrypoint for the Faro MCP server.

Run with: `uvicorn app.mcp_server.asgi:app`. The database schema is owned by
the main API service (which shares the same database and creates it on
startup); run the API at least once first in local development.
"""

from __future__ import annotations

from app.mcp_server.server import build_app

app = build_app()
