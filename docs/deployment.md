# Deployment

Faro deploys as three Railway services (API, MCP server, PostgreSQL) plus the
frontend on Vercel. Everything is driven by environment variables; no secrets
are in the repo.

## 1. AWS prerequisites

1. In the **Bedrock** console, enable model access for the models you'll use
   (e.g. an Amazon Nova or Anthropic Claude inference profile) in one region.
   Note the exact model ids — they become `MODEL_EXTRACT` and `MODEL_VERDICT`.
2. In **SES**, verify a sender identity (and, in sandbox, the demo recipient).
3. Create an **IAM user** scoped to just `bedrock:InvokeModel` on those models
   and `ses:SendEmail` from the verified identity. Save its access key/secret.

## 2. Railway — PostgreSQL

Add a PostgreSQL plugin. Railway provides `DATABASE_URL`; reference it from the
API and MCP services.

## 3. Railway — API service

- Root: `backend/` (uses `backend/Dockerfile`).
- Start command: default (`uvicorn app.main:app`).
- Variables (from `.env.example`):
  `MOCK_MODE=false`, `ENVIRONMENT=production`, `LLM_PROVIDER=bedrock`,
  `MODEL_EXTRACT`, `MODEL_VERDICT`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `BEDROCK_REGION` (if different), `SES_FROM_EMAIL`,
  `DATABASE_URL`, `JWT_SECRET` (generate a strong one), `FRONTEND_URL`,
  `ALLOWED_ORIGINS` (the Vercel URL), and optionally `TAVILY_API_KEY`.

The API creates the schema and seeds the demo account on startup.

## 4. Railway — MCP service

- Same repo/root (`backend/Dockerfile`), **override the start command**:
  `uv run uvicorn app.mcp_server.asgi:app --host 0.0.0.0 --port $PORT`
- Variables: the same AWS/model/database variables as the API, plus
  `MCP_ALLOWED_HOSTS` and `MCP_ALLOWED_ORIGINS` set to this service's **public
  host and origin** (e.g. `faro-mcp.up.railway.app` and
  `https://faro-mcp.up.railway.app`). Without these, DNS-rebinding protection
  rejects every request (see friction log #2).

The MCP endpoint for submission is `https://<mcp-host>/mcp`.

## 5. Vercel — frontend

- Root: `frontend/` (uses `frontend/vercel.json`).
- Build: `npm run build`, output `dist`.
- Variable: `VITE_API_URL=https://<api-host>` (the Railway API URL).

After the frontend URL is known, set it as `FRONTEND_URL` / `ALLOWED_ORIGINS`
on the API service and redeploy.

## 6. Smoke test

- `GET https://<api-host>/health` → `{"status":"ok"}`.
- Sign in to the frontend with `demo@faro.app` / `FaroDemo2026!` and check a
  message.
- Connect an MCP client to `https://<mcp-host>/mcp` with an
  `Authorization: Bearer <token>` header (get a token from the login endpoint)
  and call `check_message`.
