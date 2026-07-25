"""profile engine metrics

Revision ID: 20260725_0005
Revises: 20260725_0004
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260725_0005"
down_revision: str | Sequence[str] | None = "20260725_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("dataset_profiles", "total_rows", new_column_name="row_count")
    op.alter_column("dataset_profiles", "total_columns", new_column_name="column_count")
    op.alter_column("dataset_profiles", "file_size_bytes", new_column_name="source_file_size_bytes")
    op.alter_column(
        "dataset_profiles", "execution_duration_ms", new_column_name="profiling_duration_ms"
    )
    op.alter_column("dataset_profiles", "generated_at", new_column_name="profiled_at")
    op.add_column(
        "dataset_profiles",
        sa.Column("fully_null_row_percentage", sa.Float(), nullable=False, server_default="0"),
    )
    op.execute(
        """
        UPDATE dataset_profiles
        SET fully_null_row_percentage =
            CASE
                WHEN row_count = 0 THEN 0
                ELSE ROUND((fully_null_row_count::numeric / row_count::numeric) * 100, 4)
            END
        """
    )
    op.alter_column("dataset_profiles", "fully_null_row_percentage", server_default=None)
    op.add_column(
        "dataset_profiles",
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "dataset_profiles",
        sa.Column(
            "profile_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "dataset_profiles",
        sa.Column(
            "engine_version", sa.String(length=50), nullable=False, server_default="profiling-v1"
        ),
    )
    op.add_column(
        "dataset_profiles",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.add_column(
        "dataset_profiles",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.alter_column("dataset_profiles", "warnings", server_default=None)
    op.alter_column("dataset_profiles", "profile_summary", server_default=None)
    op.alter_column("dataset_profiles", "engine_version", server_default=None)
    op.create_check_constraint(
        "ck_dataset_profiles_row_count_nonnegative", "dataset_profiles", "row_count >= 0"
    )
    op.create_check_constraint(
        "ck_dataset_profiles_column_count_nonnegative", "dataset_profiles", "column_count >= 0"
    )
    op.create_check_constraint(
        "ck_dataset_profiles_duplicate_count_nonnegative",
        "dataset_profiles",
        "duplicate_row_count >= 0",
    )
    op.create_check_constraint(
        "ck_dataset_profiles_fully_null_count_nonnegative",
        "dataset_profiles",
        "fully_null_row_count >= 0",
    )
    op.create_check_constraint(
        "ck_dataset_profiles_memory_nonnegative",
        "dataset_profiles",
        "estimated_memory_bytes >= 0",
    )
    op.create_check_constraint(
        "ck_dataset_profiles_file_size_nonnegative",
        "dataset_profiles",
        "source_file_size_bytes >= 0",
    )
    op.create_check_constraint(
        "ck_dataset_profiles_duration_nonnegative",
        "dataset_profiles",
        "profiling_duration_ms >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_dataset_profiles_duration_nonnegative", "dataset_profiles")
    op.drop_constraint("ck_dataset_profiles_file_size_nonnegative", "dataset_profiles")
    op.drop_constraint("ck_dataset_profiles_memory_nonnegative", "dataset_profiles")
    op.drop_constraint("ck_dataset_profiles_fully_null_count_nonnegative", "dataset_profiles")
    op.drop_constraint("ck_dataset_profiles_duplicate_count_nonnegative", "dataset_profiles")
    op.drop_constraint("ck_dataset_profiles_column_count_nonnegative", "dataset_profiles")
    op.drop_constraint("ck_dataset_profiles_row_count_nonnegative", "dataset_profiles")
    op.drop_column("dataset_profiles", "updated_at")
    op.drop_column("dataset_profiles", "created_at")
    op.drop_column("dataset_profiles", "engine_version")
    op.drop_column("dataset_profiles", "profile_summary")
    op.drop_column("dataset_profiles", "warnings")
    op.drop_column("dataset_profiles", "fully_null_row_percentage")
    op.alter_column("dataset_profiles", "profiled_at", new_column_name="generated_at")
    op.alter_column(
        "dataset_profiles", "profiling_duration_ms", new_column_name="execution_duration_ms"
    )
    op.alter_column("dataset_profiles", "source_file_size_bytes", new_column_name="file_size_bytes")
    op.alter_column("dataset_profiles", "column_count", new_column_name="total_columns")
    op.alter_column("dataset_profiles", "row_count", new_column_name="total_rows")
