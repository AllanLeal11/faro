# Faro — a scam shield with verifiable evidence

Faro helps everyday people, and older adults in particular, recognize scams.
Paste a suspicious SMS, email or chat message and Faro tells you **whether
it's a scam, why, and what to do** — in plain language, backed by evidence you
can check. It also works by voice and exposes its tools over the Model Context
Protocol (MCP), so an assistant like Alexa+ can use it.

> In Costa Rica, the OIJ recorded **10,027 online-fraud complaints in 2025, up
> 41% from 2024** — about 27 a day. Faro is built for the people most often
> targeted: family members who aren't sure whether that "your account is
> blocked" message is real.

## Why Faro is different: it doesn't guess

Most "is this a scam?" tools just ask a model and repeat the answer. Faro
grounds every verdict in evidence and enforces two rules:

1. **The model can't invent evidence.** Deterministic checks and searches
   produce evidence items with ids; any reason the model gives that doesn't
   cite real evidence is discarded.
2. **A severe signal sets a floor.** If a deterministic check finds a
   look-alike domain, a request for a one-time code or credentials, or a
   gift-card/crypto demand, the risk can't drop below **high** — no matter
   what the model says.

The result: on the bundled sample set, Faro raises **no false alarms**, which
is what keeps a cautious user trusting it.

## Hackathon tracks

Built for the **Build, Ship, Shape: Amazon Developer Hackathon**:

- **Alexa+ (primary track)** — a self-hosted **MCP server over Streamable
  HTTP** (protocol revision 2025-11-25), exposing `check_message`,
  `add_trusted_contact` and `alert_family`. A web voice screen simulates the
  Alexa+ experience against the same tools.
- **AWS Builder (mini challenge)** — **Amazon Bedrock** (Converse API) is the
  analysis engine, and **Amazon SES** sends the family alerts.
- **Open Source (mini challenge)** — MIT licensed (see `LICENSE`).

## Try it

- **Live demo:** _(set after deployment — see Deployment below)_
- **Demo account:** `demo@faro.app` / `FaroDemo2026!` (preloaded with a
  trusted circle and a family contact; its data resets on each restart).

## How it works

```
[React web] ──HTTP──▶ [FastAPI backend] ◀──MCP (Streamable HTTP)── [Alexa+ / MCP clients]
                            │
          ┌─────────────────┼──────────────────┐
          ▼                 ▼                  ▼
   Amazon Bedrock       Tavily (optional)   PostgreSQL
   (Converse API)       live evidence       trusted circle
                            │
                        Amazon SES (family alerts)
```

The analysis pipeline (`backend/app/pipeline/`):

1. **extract** — a fast Bedrock call pulls out URLs, domains, phones, the
   claimed sender and what you're being asked to do. (Runs with no keys in
   mock mode.)
2. **checks** — deterministic Python, no LLM: look-alike / homoglyph /
   punycode domains, URL shorteners, IP-literal links, sender mismatch,
   requests for one-time codes or credentials, gift-card/crypto demands,
   urgency, and bidirectional-text tricks. This is the security floor.
3. **evidence** (optional) — a Tavily search for the organization's official
   site and scam reports. Faro never opens a link from the message.
4. **verdict** — a Bedrock reasoning call returns a risk level, confidence,
   reasons (each citing evidence), a plain explanation, a recommended action
   and a verification question.
5. **orchestration** — enforces the two rules above and degrades gracefully to
   the deterministic checks alone if a provider is unavailable.

## The MCP server (Alexa+)

Run with `uvicorn app.mcp_server.asgi:app` (or `python -m app.mcp_server`
locally). It serves Streamable HTTP at `/mcp` and negotiates protocol revision
**2025-11-25**. Every tool authenticates the caller from a per-request Bearer
token (verified locally, never forwarded), validates inputs with the same
schemas as the REST API, and reuses the same backend services. The transport
validates Origin/Host for DNS-rebinding protection.

Tools:

| Tool                 | What it does                                             |
| -------------------- | -------------------------------------------------------- |
| `check_message`      | Analyze a message; returns risk, evidence and next step. |
| `add_trusted_contact`| Register a bank/company/person in the trusted circle.    |
| `alert_family`       | Email a trusted family member (no message content).      |

## AWS usage

- **Amazon Bedrock** via the **Converse API** — one code path serves any
  Converse-capable model (Amazon Nova, Anthropic Claude, Llama…); the model
  ids are environment variables. Used at runtime by the extract and verdict
  stages (`bedrock:InvokeModel`).
- **Amazon SES** — sends the family-alert email (`ses:SendEmail` only). The
  email contains no message content, just the risk level and a verification
  question.

## Security

Faro is built security-first (see `docs/security.md` for the threat model).
Highlights: the message is never stored; secrets are masked before any model
call; the message is treated as untrusted data against prompt injection; the
deterministic floor can't be overruled by the model; URLs are defanged and
never clickable; Argon2id passwords, pinned-algorithm JWTs, per-user
authorization (404 not 403), rate limits, strict CORS and CSP, and a
fail-closed production config.

## Evaluation

`python eval/run_eval.py` compares Faro's full pipeline against a naive
single-pass baseline on a labeled set (see `eval/datasets/`). On the bundled
28-message sample, in mock mode (deterministic floor only, no live model):

| System                 | Prec. | Recall |  F1  |  FPR |
| ---------------------- | ----- | ------ | ---- | ---- |
| Faro (full pipeline)   | 1.00  | 0.75   | 0.86 | 0.00 |
| Baseline (single pass) | 0.79  | 0.92   | 0.85 | 0.19 |

Faro raises **zero false alarms** (FPR 0.00) where the baseline wrongly flags
~1 in 5 legitimate messages. Mock mode understates Faro's recall because the
model stages are simulated; run `python eval/run_eval.py --real` with Bedrock
configured to measure the full pipeline's semantic recall.

## Running locally

Backend (Python 3.13, [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv sync
cp ../.env.example .env          # MOCK_MODE=true runs with no keys
uv run uvicorn app.main:app --reload    # API on :8000
uv run python -m app.mcp_server          # MCP server on :8001
uv run pytest                            # tests
```

Frontend (Node 20+):

```bash
cd frontend
npm install
cp .env.example .env            # VITE_API_URL=http://localhost:8000
npm run dev                      # on :5173
```

## Deployment

- **Railway** — the FastAPI API, the MCP server, and PostgreSQL. Set the
  environment variables from `.env.example` (real `MODEL_EXTRACT` /
  `MODEL_VERDICT`, AWS credentials with Bedrock + SES access, `JWT_SECRET`,
  `DATABASE_URL`, `ALLOWED_ORIGINS`, `MCP_ALLOWED_HOSTS` / `MCP_ALLOWED_ORIGINS`).
- **Vercel** — the frontend, with `VITE_API_URL` pointing at the API.

## Repository layout

```
backend/     FastAPI API, analysis pipeline, MCP server, services, tests
frontend/    React + TypeScript (Vite) web app
eval/        evaluation harness + sample dataset
docs/        security model, friction log, tool feedback
CLAUDE.md    the full project specification
```

## License

MIT — see `LICENSE`.
