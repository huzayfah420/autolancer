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

    # Budget reserved for one model call before it starts (NFR-011): a call is refused when
    # today's spend plus this reservation would pass the daily cap. Mock calls reserve their
    # fixed mock cost instead.
    llm_call_reserve_usd: float = 0.02
    # Hard ceiling on output tokens per call (SEC-005).
    llm_max_output_tokens: int = 1500
    # Used to cost a call when the provider's price is unknown, so an unpriced model can
    # never spend without counting against the cap (FR-026 AC-2). USD per 1,000 tokens.
    llm_fallback_usd_per_1k_tokens: float = 0.01

    # When true, only sessions that completed MFA (Supabase `aal2`) are accepted (SEC-001).
    require_mfa: bool = False

    # Comma-separated origins allowed to call the API from a browser (the hub).
    cors_origins: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
