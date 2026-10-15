"""Tests for the MCP server wiring (app.mcp_server).

Fast, CI-safe checks: the three tools are registered with input schemas, and
the per-request Bearer authentication helper accepts a valid token and
rejects a missing or invalid one. A full Streamable HTTP round-trip against a
live server is exercised by the manual smoke script in the docs, not in CI.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.mcp_server.server import ToolError, _authenticate, build_server
from app.services.auth import create_access_token

EXPECTED_TOOLS = {"check_message", "add_trusted_contact", "alert_family"}


async def test_three_tools_registered_with_schemas():
    server = build_server()
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOLS
    for tool in tools:
        assert tool.input_schema  # each tool exposes an input schema
        assert tool.description  # fixed, in-code description (no tool poisoning)


def _ctx(headers: dict | None):
    # _authenticate only reads ctx.headers, so a duck-typed stand-in suffices.
    return SimpleNamespace(headers=headers)


def test_authenticate_accepts_valid_token():
    token = create_access_token("user-123")
    assert _authenticate(_ctx({"authorization": f"Bearer {token}"})) == "user-123"


def test_authenticate_rejects_missing_token():
    with pytest.raises(ToolError):
        _authenticate(_ctx(None))
    with pytest.raises(ToolError):
        _authenticate(_ctx({}))


def test_authenticate_rejects_bad_token():
    with pytest.raises(ToolError):
        _authenticate(_ctx({"authorization": "Bearer not-a-real-token"}))
