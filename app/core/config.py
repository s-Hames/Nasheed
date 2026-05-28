import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Vercel's serverless filesystem is read-only except /tmp
_default_db = (
    "sqlite+aiosqlite:////tmp/nasheed.db"
    if os.environ.get("VERCEL")
    else "sqlite+aiosqlite:///./nasheed.db"
)

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    """
    DATABASE_URL: str = Field(default=_default_db)
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    SCORE_THRESHOLD: int = 10
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
