"""Run the Faro MCP server locally.

`python -m app.mcp_server` creates the database schema (convenient for local
standalone runs) and serves the Streamable HTTP app on port 8001 by default.
In production the app is served by `uvicorn app.mcp_server.asgi:app` and the
schema is owned by the API service.
"""

from __future__ import annotations

import asyncio
import os

import uvicorn

from app.db.base import init_db
from app.mcp_server.asgi import app


def main() -> None:
    # Ensure tables exist for local standalone runs (no-op if already created).
    asyncio.run(init_db())
    port = int(os.environ.get("MCP_PORT", "8001"))
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
