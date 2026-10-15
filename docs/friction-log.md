# Friction log

Real friction hit while building Faro with Amazon's MCP tooling and AWS APIs.
Format per `CLAUDE.md` section 8. Allan reviews and confirms each entry.

---

### 1. The official MCP Python SDK renamed its core class (v1 → v2)

- **Task:** build the Streamable HTTP MCP server for the Alexa+ track.
- **Steps:** `uv add mcp` resolved **mcp 2.3.0**. Followed the widely
  documented v1 pattern `from mcp.server.fastmcp import FastMCP`.
- **Expected vs actual:** expected `FastMCP`; got an ImportError pointing to a
  migration guide — in 2.x `FastMCP` is renamed **`MCPServer`**
  (`from mcp.server.mcpserver import MCPServer`), and several result fields
  switched to snake_case (`protocol_version`, `is_error`, `structured_content`,
  `input_schema`).
- **Severity:** medium (blocked until the new API was learned).
- **Workaround:** introspected the installed package directly (signatures,
  model fields) and built against the real 2.x API, verified with a live
  client round-trip.
- **Suggestion:** surface the v1↔v2 split prominently in the MCP quickstart,
  and/or keep camelCase aliases on result models for a release.

---

### 2. Streamable HTTP transport security blocks everything when its allow-lists are empty

- **Task:** enable DNS-rebinding protection on the MCP transport
  (`TransportSecuritySettings`).
- **Steps:** set `enable_dns_rebinding_protection=True` (its default).
- **Expected vs actual:** expected sensible localhost defaults; actually
  `allowed_hosts` / `allowed_origins` default to **empty lists**, and with
  protection on, empty means deny-all — the server rejects every request until
  the lists are populated.
- **Severity:** medium (easy to misconfigure into a server that 4xxs
  everything, with no obvious hint why).
- **Workaround:** made the allow-lists configurable (`MCP_ALLOWED_HOSTS` /
  `MCP_ALLOWED_ORIGINS`) with explicit localhost defaults for development.
- **Suggestion:** when protection is on and both lists are empty, log a loud
  warning (or ship localhost defaults), so the failure mode is discoverable.

---

### 3. A tool returning a plain `dict` yields no `structured_content`

- **Task:** return structured results from `check_message`.
- **Steps:** typed the tool's return as `dict` and returned the analysis.
- **Expected vs actual:** expected `structured_content` to be populated;
  actually it was `None`, and the data came back only as a JSON **text**
  content block (the SDK can't infer an output schema from `dict`).
- **Severity:** low (clients can read the text JSON; it works).
- **Workaround:** documented that clients read the JSON text; the data is
  complete and valid.
- **Suggestion:** document that `structured_content` requires a typed/Pydantic
  return (or an explicit output schema), with a short example.

---

### 4. Bedrock Converse boto3 reference is very long; response syntax is past the fold

- **Task:** confirm the exact Converse response shape before writing the client.
- **Steps:** fetched the boto3 `converse` reference page.
- **Expected vs actual:** the request syntax was clear, but the page is ~119k
  characters and the **Response Syntax** section sits beyond the first screen's
  worth of content, so a quick read misses it.
- **Severity:** low.
- **Workaround:** relied on the stable, well-known shape
  (`output.message.content[0].text`, `stopReason`, `usage`) and verified field
  access defensively in code.
- **Suggestion:** a short "minimal request/response" snippet near the top of
  the Converse reference would save a lot of scrolling.
