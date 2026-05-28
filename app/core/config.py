import os

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    """
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./nasheed.db")
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

    @model_validator(mode="after")
    def _force_tmp_db_on_vercel(self) -> "Settings":
        """
        Vercel's serverless filesystem is read-only except /tmp.
        Force SQLite to use /tmp regardless of other configuration sources.
        """
        if os.environ.get("VERCEL") and "sqlite" in self.DATABASE_URL:
            self.DATABASE_URL = "sqlite+aiosqlite:////tmp/nasheed.db"
        return self

settings = Settings()

