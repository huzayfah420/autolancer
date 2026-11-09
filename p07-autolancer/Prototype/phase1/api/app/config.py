"""Settings read from environment variables (or a gitignored .env file).

Every variable is documented in .env.example and the README.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLAlchemy URL. SQLite for local dev/tests, Supabase Postgres in production.
    database_url: str = "sqlite:///./autolancer.db"

    # Supabase project URL, used to fetch the JWKS for asymmetric (ES256/RS256) tokens.
    supabase_url: str = ""
    # Legacy HS256 secret. If set, tokens are verified with it instead of JWKS.
    supabase_jwt_secret: str = ""

    # Base URL of the marketplace simulator. The API only talks to it over HTTP.
    simulator_url: str = "http://localhost:8000/sim"

    # LiteLLM model name, e.g. "deepseek/deepseek-chat". "mock" = deterministic fake output.
    llm_model: str = "mock"
    llm_timeout_seconds: float = 60.0

    # Daily AI cap used only before the owner has saved any policy version.
    default_daily_ai_cap_usd: float = 0.50

    # Comma-separated origins allowed to call the API from a browser (the hub).
    cors_origins: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
