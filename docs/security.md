# Security

This document tracks Faro's threat model, the controls in place, and what's
still missing before the app is safe to run in public. It follows CLAUDE.md
section 12 and is updated as the project grows — it describes what's
actually built today, not the target state.

Last updated: 2026-09-21 (backend pipeline stage: `extract.py`/`checks.py`
built; no HTTP API, database, auth, or MCP server yet).

## Scope and assets

Faro analyzes a message a user pastes in (SMS/email/WhatsApp text) and
tells them whether it looks like a scam. The things worth protecting:

- **The analyzed message itself.** Per CLAUDE.md section 5, it is never
  persisted — not in the database, not in logs. Today (pipeline-only,
  no API/DB yet) this is enforced by simply never writing it anywhere;
  once the API and database exist, this needs an explicit test.
- **The user's trusted circle** (bank/company/contact names, domains,
  phones, emails) and family contacts — persisted, and the main target
  for IDOR/BOLA once multi-user auth exists.
- **Third-party API keys** (Nebius Token Factory, Tavily, AWS SES,
  database credentials, JWT secret) — server-side only, never in the
  frontend, never in a prompt sent to an LLM.
- **Faro's own verdicts**, which an elderly or otherwise vulnerable user
  may act on directly — a false "this is safe" is as dangerous as a
  compromise of the service itself, so the deterministic-floor rule
  (section 12.7: a severe `checks.py` finding can't be overridden by the
  LLM) is treated as a security control, not just a quality one.

## Threat model summary

| Actor | Wants | Mitigated by |
|---|---|---|
| Attacker submitting a crafted message | Get the LLM to act on instructions embedded in the message; exfiltrate other users' data; make Faro call an attacker-controlled URL | `extract.py`'s untrusted-data prompt framing (12.7); Faro never fetches a URL from a message (12.6); auth/IDOR controls (12.4, not built yet) |
| Attacker on the network | Read/tamper with traffic | HTTPS-only + HSTS + strict CORS (12.2) — see `middleware/security.py` |
| Attacker with a stolen/forged token | Access another user's data | JWT validation, `user_id` from token only (12.3/12.4 — auth not built yet) |
| Malicious dependency or compromised GitHub Action | Supply-chain compromise | Locked dependencies, pinned Action SHAs, Dependabot, `pip-audit`/`bandit`/`gitleaks`/`semgrep` in CI (12.11/12.12) |
| Anyone with repo access history | Find a leaked secret | `detect-secrets`/`detect-private-key` pre-commit + `gitleaks` in CI scanning full history (12.1) |

## Controls implemented so far

**Transport & headers** (`backend/app/middleware/security.py`,
`backend/app/main.py`):
- Strict `Content-Security-Policy` (`default-src 'none'`, no inline
  scripts), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`,
  `Permissions-Policy: microphone=(self)`, HSTS in production.
- CORS restricted to `ALLOWED_ORIGINS`, `allow_credentials=False`.
- Request body size capped (`BodySizeLimitMiddleware`) ahead of any route.
- `/docs`/`/redoc`/`/openapi.json` only exist when `ENVIRONMENT=development`.
- No stack traces or internals returned to the client on any error path
  (generic 500, validation errors don't echo server internals).

**Config** (`backend/app/config.py`):
- Fails closed in production: refuses to start with `MOCK_MODE=true`, a
  missing/wildcarded `ALLOWED_ORIGINS`, or any missing required secret.

**Pipeline** (`backend/app/pipeline/`):
- `redact.py` strips card numbers, OTP codes, and passwords from the
  message text before it reaches the Nebius LLM call (12.7). Regressions
  here are tested for both keyword-before-digits and digits-before-keyword
  phrasing (the latter is how real bank OTP texts are usually worded),
  and for `.`/`,`/`-`/space card separators.
- `extract.py` frames the message as delimited, untrusted data with an
  explicit system instruction never to follow instructions found inside
  it; the LLM's JSON output is strictly schema-validated (Pydantic,
  `extra="forbid"`) before use, and a bad/missing/timed-out response
  raises instead of silently returning guessed data.
- `checks.py` never renders a suspicious domain/URL as live text — every
  one is defanged (`hxxps://banco-falso[.]com`) before it goes into an
  evidence `detail` string, so it can never become a clickable link or
  auto-linked markup downstream.
- No `eval`, `exec`, `pickle`, or `yaml.load` anywhere in the codebase.
- All regexes use bounded quantifiers (explicit `{m,n}` caps, no nested
  unbounded repetition) to avoid catastrophic backtracking.

**CI** (`.github/workflows/ci.yml`, `.pre-commit-config.yaml`):
- `gitleaks` scans full git history on every push/PR (secret scanning).
- `semgrep` static analysis (`--config auto`) on every push/PR.
- `bandit` static analysis and `pip-audit` dependency scanning on every
  push/PR.
- `ruff check`/`ruff format --check` and the full `pytest` suite gate
  every push/PR.
- `detect-secrets` and `detect-private-key` run locally as pre-commit
  hooks (fast, dependency-free first line of defense).
- Dependabot watches the backend's `uv` lockfile and the GitHub Actions
  themselves (`.github/dependabot.yml`).
- Actions are pinned (`astral-sh/setup-uv` by commit SHA) where the
  upstream project publishes one, to resist tag-mutation supply-chain
  attacks.

## Known gaps — not built yet

These are not oversights; they're simply the parts of CLAUDE.md section 12
that don't apply until the corresponding feature exists. Tracked here so
none of them get skipped when that feature is built:

- **No HTTP API yet** → nothing in section 12.3 (auth/sessions), 12.4
  (IDOR/BOLA authorization tests), or 12.9 (per-user/per-IP rate limits)
  is implemented. `MAX_MESSAGE_CHARS = 5000` is enforced in `extract.py`
  itself as a head start, but the API layer needs its own Pydantic
  `max_length` + request-size validation when it's built.
- **No database yet** → no SSL/private-network Postgres config, no
  `trusted_entities`/`family_contacts`/`alerts` tables, so no IDOR
  surface exists to test yet.
- **No MCP server yet** → section 12.8 (session auth, `Origin` header
  validation, no token forwarding) is entirely pending.
- **No SES integration yet** → section 12.5's email-header-injection
  rule (strip CR/LF from subjects/recipients) applies once `alert_family`
  is built.
- **No Tavily integration yet** → section 12.7's "Tavily results are also
  untrusted data" rule, and 12.6's SSRF rule (queries only, never fetch a
  URL from the message), apply once `evidence.py` is built.
- **No frontend yet** → XSS rules (plain-text rendering, no
  `dangerouslySetInnerHTML`, defanged non-clickable suspicious URLs) apply
  once it exists; `checks.py` already produces defanged text so the
  frontend has nothing extra to sanitize for that specific case.
- **OWASP ZAP baseline scan**: not run yet — there's no deployed instance
  to scan. Planned for the deploy/polish phase (CLAUDE.md section 10,
  Oct 10–18), against Faro's own deployment only, never a third party.
- **Container hardening** (minimal base image, non-root user): pending
  Railway deployment setup.

## Reporting a vulnerability

This is a hackathon project in active development. If you find a security
issue, please open a private report to the repository owner rather than a
public issue.
