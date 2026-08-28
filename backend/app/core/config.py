from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "RecoverIQ"
    debug: bool = False

    # Database
    database_url: str = "postgresql://localhost:5432/recoveriq"

    # Supabase (future)
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # Razorpay (future — test mode only)
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    # LLM (future)
    llm_api_key: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def get_settings() -> Settings:
    """Return application settings instance."""
    return Settings()
