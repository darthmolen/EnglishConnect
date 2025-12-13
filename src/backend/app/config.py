"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Application
    app_name: str = "EnglishConnect"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://englishconnect:devpassword@localhost:5432/englishconnect"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Claude API
    anthropic_api_key: str = ""

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o-mini"
    azure_openai_api_version: str = "2024-10-21"

    # OAuth - Google
    google_client_id: str = ""
    google_client_secret: str = ""

    # OAuth - Microsoft (optional)
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""

    # Voice Services (local endpoints for POC)
    stt_service_url: str = "http://localhost:8001"
    tts_mcp_url: str = "http://localhost:8002"
    content_mcp_url: str = "http://localhost:8003"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
