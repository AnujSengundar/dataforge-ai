from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.database import engine


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url="postgresql+psycopg2://postgres:password@localhost:5432/dataforge",
        upload_dir=str(tmp_path / "uploads"),
        max_upload_mb=50,
        app_env="test",
        high_null_threshold=0.40,
        categorical_unique_ratio_threshold=0.05,
        identifier_unique_ratio_threshold=0.98,
        type_coercion_sample_size=1000,
        profile_sample_values=5,
        profile_sample_max_chars=20,
        category_value_limit=25,
        null_rate_drift_threshold=5.0,
        cardinality_drift_threshold=0.20,
        numeric_drift_threshold=0.20,
        quality_row_weight=0.70,
        quality_rule_weight=0.30,
    )


@pytest.fixture
def db_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
