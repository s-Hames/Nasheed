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
        is_vercel = (
            os.environ.get("VERCEL") is not None
            or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
            or not os.access(".", os.W_OK)
        )
        if is_vercel and "sqlite" in self.DATABASE_URL:
            self.DATABASE_URL = "sqlite+aiosqlite:////tmp/nasheed.db"
            
            # Copy existing packaged db to /tmp if it exists and hasn't been copied yet.
            # This preserves any pre-seeded data/cached videos from the local SQLite db.
            import shutil
            src_db = "./nasheed.db"
            dest_db = "/tmp/nasheed.db"
            if os.path.exists(src_db) and not os.path.exists(dest_db):
                try:
                    shutil.copyfile(src_db, dest_db)
                except Exception as e:
                    print(f"Failed to copy packaged nasheed.db to /tmp: {e}")
            
            # Ensure the copied database is explicitly writable, as files copied from the
            # read-only lambda package directory may inherit read-only permission flags.
            if os.path.exists(dest_db):
                try:
                    os.chmod(dest_db, 0o666)
                except Exception as e:
                    print(f"Failed to set write permissions on /tmp/nasheed.db: {e}")
        return self

settings = Settings()

