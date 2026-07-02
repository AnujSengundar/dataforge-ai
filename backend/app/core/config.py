import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    upload_dir: str
    max_upload_mb: int
    app_env: str

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:password@localhost:5432/dataforge",
        ),
        upload_dir=os.getenv("UPLOAD_DIR", "uploads"),
        max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "50")),
        app_env=os.getenv("APP_ENV", "development"),
    )
