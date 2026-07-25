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
    identifier_unique_threshold: float
    identifier_max_null_percentage: float
    categorical_unique_threshold: float
    categorical_max_distinct: int
    type_coercion_sample_size: int
    numeric_text_match_threshold: float
    datetime_text_match_threshold: float
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
        high_null_threshold=_percent("PROFILE_HIGH_NULL_THRESHOLD", "40.0"),
        identifier_unique_threshold=_percent("PROFILE_IDENTIFIER_UNIQUE_THRESHOLD", "98.0"),
        identifier_max_null_percentage=_percent("PROFILE_IDENTIFIER_MAX_NULL_PERCENTAGE", "1.0"),
        categorical_unique_threshold=_percent("PROFILE_CATEGORICAL_UNIQUE_THRESHOLD", "5.0"),
        categorical_max_distinct=_positive_int("PROFILE_CATEGORICAL_MAX_DISTINCT", "100"),
        type_coercion_sample_size=_positive_int("PROFILE_TYPE_COERCION_SAMPLE_SIZE", "1000"),
        numeric_text_match_threshold=_percent("PROFILE_NUMERIC_TEXT_MATCH_THRESHOLD", "95.0"),
        datetime_text_match_threshold=_percent("PROFILE_DATETIME_TEXT_MATCH_THRESHOLD", "95.0"),
        profile_sample_values=_positive_int("PROFILE_SAMPLE_VALUES", "5"),
        profile_sample_max_chars=_positive_int("PROFILE_SAMPLE_MAX_CHARS", "200"),
        category_value_limit=_positive_int("PROFILE_CATEGORY_VALUE_LIMIT", "25"),
        null_rate_drift_threshold=float(os.getenv("NULL_RATE_DRIFT_THRESHOLD", "5.0")),
        cardinality_drift_threshold=float(os.getenv("CARDINALITY_DRIFT_THRESHOLD", "0.20")),
        numeric_drift_threshold=float(os.getenv("NUMERIC_DRIFT_THRESHOLD", "0.20")),
        quality_row_weight=float(os.getenv("QUALITY_ROW_WEIGHT", "0.70")),
        quality_rule_weight=float(os.getenv("QUALITY_RULE_WEIGHT", "0.30")),
    )


def _percent(name: str, default: str) -> float:
    value = float(os.getenv(name, default))
    if not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100.")
    return value


def _positive_int(name: str, default: str) -> int:
    value = int(os.getenv(name, default))
    if value <= 0:
        raise ValueError(f"{name} must be positive.")
    return value
