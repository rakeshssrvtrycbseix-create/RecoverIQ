from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "RecoverIQ"
    debug: bool = False

    # Database
    database_url: str

    # Supabase (future)
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # Razorpay Provider Configuration
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    razorpay_base_url: str = "https://api.razorpay.com/v1"
    razorpay_timeout_seconds: float = 10.0

    # Provider & Live Action Governance
    recovery_provider: str = "mock"  # "mock" | "razorpay"
    allow_live_financial_actions: bool = False
    action_reconciliation_timeout_minutes: int = 15

    # LLM (future)
    llm_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
