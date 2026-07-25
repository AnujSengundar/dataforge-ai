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
    high_null_threshold: float
    categorical_unique_ratio_threshold: float
    identifier_unique_ratio_threshold: float
    type_coercion_sample_size: int
    profile_sample_values: int
    profile_sample_max_chars: int
    category_value_limit: int
    null_rate_drift_threshold: float
    cardinality_drift_threshold: float
    numeric_drift_threshold: float
    quality_row_weight: float
    quality_rule_weight: float

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
        high_null_threshold=float(os.getenv("PROFILE_HIGH_NULL_THRESHOLD", "0.40")),
        categorical_unique_ratio_threshold=float(
            os.getenv("PROFILE_CATEGORICAL_UNIQUE_RATIO_THRESHOLD", "0.05")
        ),
        identifier_unique_ratio_threshold=float(
            os.getenv("PROFILE_IDENTIFIER_UNIQUE_RATIO_THRESHOLD", "0.98")
        ),
        type_coercion_sample_size=int(os.getenv("PROFILE_TYPE_COERCION_SAMPLE_SIZE", "1000")),
        profile_sample_values=int(os.getenv("PROFILE_SAMPLE_VALUES", "5")),
        profile_sample_max_chars=int(os.getenv("PROFILE_SAMPLE_MAX_CHARS", "200")),
        category_value_limit=int(os.getenv("PROFILE_CATEGORY_VALUE_LIMIT", "25")),
        null_rate_drift_threshold=float(os.getenv("NULL_RATE_DRIFT_THRESHOLD", "5.0")),
        cardinality_drift_threshold=float(os.getenv("CARDINALITY_DRIFT_THRESHOLD", "0.20")),
        numeric_drift_threshold=float(os.getenv("NUMERIC_DRIFT_THRESHOLD", "0.20")),
        quality_row_weight=float(os.getenv("QUALITY_ROW_WEIGHT", "0.70")),
        quality_rule_weight=float(os.getenv("QUALITY_RULE_WEIGHT", "0.30")),
    )
