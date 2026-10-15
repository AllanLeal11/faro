"""Application settings.

Reads every variable from .env.example (see CLAUDE.md section 8) via
pydantic-settings. Fails closed: in production, a missing secret or a
misconfigured ALLOWED_ORIGINS refuses to start rather than run insecurely.

LLM provider: the analysis pipeline talks to a provider-agnostic client
(see app/services/llm.py). The default is AWS Bedrock, which also covers the
Amazon "AWS Builder" mini challenge. The `nebius` option is retained so the
same codebase can target the Nebius hackathon without edits — only env vars
change.
"""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["bedrock", "nebius"]


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
        required: dict[str, str] = {
            "MODEL_EXTRACT": self.model_extract,
            "MODEL_VERDICT": self.model_verdict,
            "DATABASE_URL": self.database_url,
            "JWT_SECRET": self.jwt_secret,
            "SES_FROM_EMAIL": self.ses_from_email,
            "FRONTEND_URL": self.frontend_url,
            # SES needs AWS credentials even when the LLM provider is Nebius.
            "AWS_REGION": self.aws_region,
            "AWS_ACCESS_KEY_ID": self.aws_access_key_id,
            "AWS_SECRET_ACCESS_KEY": self.aws_secret_access_key,
        }

        # Provider-specific requirements.
        if self.llm_provider == "nebius":
            required["NEBIUS_API_KEY"] = self.nebius_api_key
            required["NEBIUS_BASE_URL"] = self.nebius_base_url
        # Bedrock reuses the AWS credentials already required above.

        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                f"Missing required environment variables in production: {', '.join(missing)}"
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
