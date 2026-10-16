"""Application settings.

Reads every variable from .env.example (see CLAUDE.md section 8) via
pydantic-settings. Fails closed: in production, a missing secret or a
misconfigured ALLOWED_ORIGINS refuses to start rather than run insecurely.

LLM provider: the analysis pipeline talks to a provider-agnostic client
(see app/services/llm.py). Options:
- `bedrock` — AWS Bedrock Converse (also covers the AWS Builder mini
  challenge); needs AWS credentials.
- `google` — Google Gemini via its OpenAI-compatible endpoint; needs only a
  free Gemini API key (no AWS, no card). Used for the zero-cost deployment.
- `nebius` — OpenAI-compatible Token Factory, for the Nebius hackathon.

SES (family-alert email) is optional: when AWS credentials and a verified
sender are not configured, the alert is simulated (logged, reported sent) so
the feature still demos without AWS.
"""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["bedrock", "google", "nebius"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App mode ---
    mock_mode: bool = True
    environment: str = "development"

    # --- LLM provider selection ---
    llm_provider: LLMProvider = "bedrock"
    # Model ids / inference-profile ids for the two pipeline stages. For
    # Bedrock these come from the user's Bedrock console (e.g. a Nova or
    # Claude inference profile); for Nebius they are Nemotron model ids.
    model_extract: str = ""
    model_verdict: str = ""

    # --- AWS (Bedrock + SES share these credentials) ---
    aws_region: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    # Bedrock may live in a different region than SES; defaults to aws_region.
    bedrock_region: str = ""
    ses_from_email: str = ""

    # --- Google Gemini (only used when llm_provider == "google") ---
    # A free API key from Google AI Studio (no AWS, no card).
    google_api_key: str = ""

    # --- Nebius Token Factory (only used when llm_provider == "nebius") ---
    nebius_api_key: str = ""
    nebius_base_url: str = ""

    # --- Tavily (optional evidence search) ---
    # When empty, the evidence stage is skipped and results are marked partial.
    tavily_api_key: str = ""

    # --- Database ---
    database_url: str = ""

    # --- Auth ---
    jwt_secret: str = ""

    # --- Web / CORS ---
    frontend_url: str = ""
    allowed_origins: str = ""

    # --- MCP server (Streamable HTTP) ---
    # Comma-separated allow-lists for the MCP transport's DNS-rebinding
    # protection (CLAUDE.md 12.8). In production set these to the MCP server's
    # public host/origin; in development they default to localhost.
    mcp_allowed_hosts: str = ""
    mcp_allowed_origins: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def effective_bedrock_region(self) -> str:
        return self.bedrock_region or self.aws_region

    @property
    def ses_configured(self) -> bool:
        """True only when SES can actually send (creds + verified sender)."""
        return bool(
            self.aws_access_key_id
            and self.aws_secret_access_key
            and self.aws_region
            and self.ses_from_email
        )

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def mcp_allowed_hosts_list(self) -> list[str]:
        configured = [h.strip() for h in self.mcp_allowed_hosts.split(",") if h.strip()]
        if configured:
            return configured
        # Dev default: localhost on any port. Production must configure this.
        return ["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*"]

    @property
    def mcp_allowed_origins_list(self) -> list[str]:
        configured = [o.strip() for o in self.mcp_allowed_origins.split(",") if o.strip()]
        if configured:
            return configured
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def effective_database_url(self) -> str:
        """The async SQLAlchemy URL to connect with.

        In production DATABASE_URL is required (validated below). In
        development, an empty value falls back to a local SQLite file so the
        app runs with no external database. A plain `postgresql://` URL (as
        Railway provides) is normalized to the asyncpg driver.
        """
        url = self.database_url.strip()
        if not url:
            return "sqlite+aiosqlite:///./faro.db"
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @model_validator(mode="after")
    def _fail_closed_in_production(self) -> "Settings":
        """Refuse to start in production with an insecure or incomplete config.

        This is the "fail closed" principle from CLAUDE.md section 12: when
        in doubt, block. A missing secret or an unrestricted CORS policy in
        production is not a warning, it's a startup error.
        """
        if not self.is_production:
            return self

        if self.mock_mode:
            raise ValueError("MOCK_MODE must be false in production.")

        if not self.allowed_origins_list:
            raise ValueError("ALLOWED_ORIGINS must be set in production.")
        if "*" in self.allowed_origins_list:
            raise ValueError("ALLOWED_ORIGINS must not contain '*' in production.")

        # Always required in production, regardless of LLM provider.
        # DATABASE_URL is intentionally optional: without it the app uses a
        # local SQLite file, which is fine for the free demo (the schema is
        # recreated and the demo account re-seeded on startup).
        required: dict[str, str] = {
            "MODEL_EXTRACT": self.model_extract,
            "MODEL_VERDICT": self.model_verdict,
            "JWT_SECRET": self.jwt_secret,
            "FRONTEND_URL": self.frontend_url,
        }

        # Provider-specific requirements.
        if self.llm_provider == "bedrock":
            required["AWS_ACCESS_KEY_ID"] = self.aws_access_key_id
            required["AWS_SECRET_ACCESS_KEY"] = self.aws_secret_access_key
            required["AWS_REGION"] = self.aws_region
        elif self.llm_provider == "google":
            required["GOOGLE_API_KEY"] = self.google_api_key
        elif self.llm_provider == "nebius":
            required["NEBIUS_API_KEY"] = self.nebius_api_key
            required["NEBIUS_BASE_URL"] = self.nebius_base_url

        # SES is optional. If a sender is set, require full credentials so a
        # half-configured SES doesn't silently fail; if none is set, alerts
        # are simulated (see services/ses.py).
        if self.ses_from_email:
            required["AWS_ACCESS_KEY_ID"] = self.aws_access_key_id
            required["AWS_SECRET_ACCESS_KEY"] = self.aws_secret_access_key
            required["AWS_REGION"] = self.aws_region

        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                f"Missing required environment variables in production: {', '.join(missing)}"
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
