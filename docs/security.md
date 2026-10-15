# Security model

Faro follows defense in depth, secure-by-default and **fail closed** (when in
doubt, block or mark high risk). This document summarizes the threat model and
the main controls; the full requirements live in `CLAUDE.md` section 12.

## Assets and privacy

- **Analyzed messages are never stored.** They live only in the single
  in-memory request. The short-lived verdict cache is keyed by a salted hash
  and holds only the result object, which contains no message text.
- Only the trusted circle, family contacts and alert metadata (risk level and
  timestamp, **no message content**) are persisted.

## Authentication and sessions

- Passwords hashed with **Argon2id**.
- **JWTs** signed HS256 with a pinned algorithm (rejects `none` and
  algorithm-confusion), carrying and verifying `exp`, `iss` and `aud`.
- The access token is held **in memory by the SPA** — never in `localStorage`
  or a cookie.

### Why a memory-only Bearer token instead of a cookie + CSRF

`CLAUDE.md` 12.3 specifies an httpOnly, SameSite cookie plus a CSRF token. In
this deployment the frontend (Vercel) and backend (Railway) are on **different
domains**, where a `SameSite` cookie would not be sent and a cross-site cookie
would weaken CSRF posture. A memory-only Bearer token, sent in the
`Authorization` header, has **no ambient credential**, so there is no CSRF
surface at all. It is also the natural fit for the MCP server, which
authenticates each request with a per-user Bearer token. The trade-off: a page
refresh signs the user out; the one-tap demo login makes that a non-issue for
judges. This deviation was reviewed and approved.

## Authorization (IDOR / BOLA)

- Every data-access query is scoped by the `user_id` from the token; the
  client never supplies a `user_id`.
- Accessing a missing or foreign row returns **404, not 403**, so existence
  isn't leaked. Tests assert that user A cannot read, edit or delete user B's
  rows, over both the API and MCP.

## Input validation and injection

- All request models set `extra="forbid"` (no mass assignment); emails,
  domains and phones are format-validated; messages are capped at 5,000 chars
  with a request-body size limit.
- Regexes are length-bounded and free of nested quantifiers (anti-ReDoS).
- The analyzed message and model output are shown as **plain text**;
  suspicious URLs are **defanged** (`hxxps://bad[.]com`) and never clickable.
  Only official evidence sources can be links (https, `rel="noopener
  noreferrer nofollow"`).
- Unicode is NFKC-normalized; homoglyphs, punycode and bidirectional-control
  characters are detected and neutralized.

## LLM security (OWASP LLM Top 10)

- The message is delimited as **untrusted data**; system prompts forbid
  following instructions inside it. Tavily results are treated the same way.
- **Deterministic floor:** a severe check forces risk ≥ high; the model can't
  lower it.
- **No invented evidence:** reasons citing unknown evidence ids are discarded.
- The verdict stage has **no tools and no side effects**.
- Card numbers, one-time codes and passwords are **masked before** any text
  reaches a model or Tavily. Prompts never contain secrets.

## MCP server

- Per-request Bearer authentication; tokens are verified locally and never
  forwarded to external services.
- Streamable HTTP transport validates **Origin/Host** (DNS-rebinding
  protection) via an allow-list.
- Tool inputs use the same schemas as the API; `alert_family` only accepts the
  caller's own contacts and honors the same rate limits.
- Tool descriptions are fixed in code (no tool poisoning); responses defang
  URLs and flag message content as untrusted.

## Transport, secrets and availability

- HTTPS only; HSTS in production; outbound calls verify TLS with timeouts.
- Strict CSP (no inline scripts), `X-Content-Type-Options`, `frame-ancestors
  'none'`, `Referrer-Policy`, and a `Permissions-Policy` that allows the
  microphone only on the same origin.
- Secrets only in backend environment variables; `.env` is gitignored;
  pre-commit runs `detect-private-key` and `detect-secrets`, and CI adds
  `gitleaks`, `bandit` and `ruff`.
- Per-user / per-IP rate limits on checks, logins and alerts; external-call
  timeouts; a fail-closed production config that refuses to start if a secret
  or CORS allow-list is missing.

## Residual risks

- The in-memory rate limiter and verdict cache are per-process; a multi-
  instance deployment should move them to Redis.
- SES in sandbox mode only sends to verified addresses (fine for the demo).
- The registrable-domain heuristic covers common cases, not the full public
  suffix list.
- Mock mode is for development only and must be off in production (enforced).
