"""Application settings.

Reads every variable from .env.example (see CLAUDE.md section 8) via
pydantic-settings. Fails closed: in production, a missing secret or a
misconfigured ALLOWED_ORIGINS refuses to start rather than run insecurely.
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App mode ---
    mock_mode: bool = True
    environment: str = "development"

    # --- Nebius Token Factory ---
    nebius_api_key: str = ""
    nebius_base_url: str = ""
    model_extract: str = ""
    model_verdict: str = ""

    # --- Tavily ---
    tavily_api_key: str = ""

    # --- Database ---
    database_url: str = ""

    # --- Auth ---
    jwt_secret: str = ""

    # --- Amazon SES ---
    aws_region: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    ses_from_email: str = ""

    # --- Web / CORS ---
    frontend_url: str = ""
    allowed_origins: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

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

        required = {
            "NEBIUS_API_KEY": self.nebius_api_key,
            "NEBIUS_BASE_URL": self.nebius_base_url,
            "MODEL_EXTRACT": self.model_extract,
            "MODEL_VERDICT": self.model_verdict,
            "TAVILY_API_KEY": self.tavily_api_key,
            "DATABASE_URL": self.database_url,
            "JWT_SECRET": self.jwt_secret,
            "AWS_REGION": self.aws_region,
            "AWS_ACCESS_KEY_ID": self.aws_access_key_id,
            "AWS_SECRET_ACCESS_KEY": self.aws_secret_access_key,
            "SES_FROM_EMAIL": self.ses_from_email,
            "FRONTEND_URL": self.frontend_url,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                f"Missing required environment variables in production: {', '.join(missing)}"
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
