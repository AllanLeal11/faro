"""Run entrypoint used by `uv run python -m app` and by Railway.

Chooses the listen interface from ENVIRONMENT (CLAUDE.md section 12.8):
127.0.0.1 in development, to resist DNS rebinding on a local machine;
0.0.0.0 in production, which is what the container needs to accept
traffic. The port always comes from Railway's PORT variable.
"""

import os

import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    # Binding to all interfaces is intentional and gated: only in
    # production, where the Railway container needs it to receive
    # traffic. Locally (the default) this always binds 127.0.0.1.
    host = "0.0.0.0" if settings.is_production else "127.0.0.1"  # noqa: S104 # nosec B104
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port)


if __name__ == "__main__":
    main()
