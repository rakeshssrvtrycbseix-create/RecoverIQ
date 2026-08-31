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

    # Background Worker Settings
    action_poll_interval_seconds: float = 10.0
    reconciliation_interval_seconds: float = 300.0
    worker_batch_size: int = 50

    # LLM (future)
    llm_api_key: str = ""

    # Security & Authentication (JWT & API Keys)
    jwt_secret_key: str = "recoveriq_dev_jwt_secret_change_in_production_998877"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440  # 24 hours
    jwt_issuer: str = "RecoverIQ"
    admin_api_key: str = ""  # Optional secret for machine-to-machine admin access

    # Phase 10A: Security Hardening, Threat Detection & Fintech Trust Layer
    cors_allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    rate_limit_enabled: bool = True
    rate_limit_auth_per_minute: int = 15
    rate_limit_webhooks_per_minute: int = 120
    rate_limit_mutations_per_minute: int = 60
    rate_limit_reads_per_minute: int = 240
    webhook_timestamp_tolerance_seconds: int = 0  # 0 = disabled (dev/test default); set to e.g. 300 in production for replay protection
    max_request_body_bytes: int = 1_048_576  # 1 MB
    enable_security_headers: bool = True
    enable_pii_scanner: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
