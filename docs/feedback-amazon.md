# Tool feedback — Amazon Developer Hackathon

Feedback on each Amazon tool, API and SDK used to build Faro. Runtime notes
marked _(pending live keys)_ will be completed once the project is deployed
with real AWS credentials.

## Amazon Bedrock — Converse API (`bedrock-runtime`)

- **Used for:** the analysis engine. The extract and verdict pipeline stages
  call `converse` at runtime; the model id is an environment variable.
- **Worked well:** one API (`converse`) serves any Converse-capable model —
  Amazon Nova, Anthropic Claude, Llama — so switching models is a config
  change, not a code change. The request shape (`system`, `messages`,
  `inferenceConfig`) is clean and the system/user separation made prompt-
  injection hardening straightforward.
- **Needs work:** the boto3 reference page is enormous and the response syntax
  is far down it (see friction log #4). A short canonical request/response
  snippet, and clearer guidance on when a region needs an inference-profile id
  prefix (e.g. `us.` / `eu.`) vs a bare model id, would help first-time users.
- **Onboarding:** enabling model access per-region in the console is an easy
  step to miss; a one-line "you must enable access first" callout near the
  model-id docs would reduce confusion.
- **Would use again:** yes. The model-agnostic Converse surface is exactly
  right for a project that wants to stay portable across models.
- **Runtime notes:** _(pending live keys)_ latency and token costs for the two
  stages on the chosen model.

## Amazon SES (`ses:SendEmail`)

- **Used for:** the family-alert email (no message content — only the risk
  level and a verification question).
- **Worked well:** the `send_email` call is simple, and scoping an IAM user to
  `ses:SendEmail` from a single verified identity is clear least-privilege.
- **Needs work:** the sandbox's "verified recipients only" rule is easy to
  forget when a demo email silently doesn't arrive; surfacing that state in the
  send response (rather than only in the console) would help.
- **Onboarding:** identity verification is straightforward.
- **Would use again:** yes.
- **Runtime notes:** _(pending live keys)_ deliverability and bounce handling.

## Model Context Protocol — Python SDK (`mcp` 2.3.0)

- **Used for:** the Alexa+ track MCP server (Streamable HTTP, protocol
  2025-11-25) exposing three tools.
- **Worked well:** once on the right API, `MCPServer` + the `@tool` decorator
  made tool definitions concise, `Context.headers` gave clean per-request
  Bearer auth, and `streamable_http_app(...)` produced a ready ASGI app that
  negotiated protocol 2025-11-25 with a standard client on the first try.
  `TransportSecuritySettings` for Origin/Host validation is a thoughtful,
  built-in defense.
- **Needs work:** the v1→v2 rename (`FastMCP` → `MCPServer`) and the
  snake_case result fields are a real stumbling block for anyone following
  existing tutorials (friction log #1); the empty-allow-list deny-all behavior
  is easy to trip over (friction log #2); and `dict` returns don't produce
  `structured_content` (friction log #3).
- **Onboarding:** the SDK is capable, but current public examples mostly show
  the v1 API, so the fastest path was reading the installed source.
- **Would use again:** yes — the Streamable HTTP story is solid and the
  security primitives are welcome.
