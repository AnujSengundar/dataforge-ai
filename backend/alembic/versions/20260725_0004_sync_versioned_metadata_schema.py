"""sync versioned metadata schema

Revision ID: 20260725_0004
Revises: b02c686b9f51
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260725_0004"
down_revision: str | Sequence[str] | None = "b02c686b9f51"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("datasets", sa.Column("name", sa.String(length=255), nullable=True))
    op.add_column("datasets", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "datasets", sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.execute(
        """
        UPDATE datasets
        SET name = COALESCE(NULLIF(original_filename, ''), 'dataset-' || id::text)
        WHERE name IS NULL
        """
    )
    op.alter_column("datasets", "name", nullable=False)
    op.alter_column("datasets", "original_filename", existing_type=sa.String(255), nullable=True)
    op.alter_column("datasets", "stored_filename", existing_type=sa.String(255), nullable=True)
    op.alter_column("datasets", "file_path", existing_type=sa.String(1024), nullable=True)
    op.alter_column("datasets", "file_hash", existing_type=sa.String(64), nullable=True)
    op.alter_column("datasets", "file_size_bytes", existing_type=sa.Integer(), nullable=True)
    op.drop_index("ix_datasets_file_hash", table_name="datasets")
    op.create_index(op.f("ix_datasets_file_hash"), "datasets", ["file_hash"], unique=False)

    op.create_table(
        "dataset_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("file_format", sa.String(length=20), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("row_count", sa.BigInteger(), nullable=True),
        sa.Column("column_count", sa.Integer(), nullable=True),
        sa.Column("processing_status", sa.String(length=50), nullable=False),
        sa.Column("ingestion_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingestion_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("schema_signature", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "version_number", name="uq_dataset_versions_number"),
        sa.UniqueConstraint("dataset_id", "sha256_hash", name="uq_dataset_versions_hash"),
    )
    op.create_index(
        "ix_dataset_versions_dataset_created", "dataset_versions", ["dataset_id", "created_at"]
    )
    op.create_index(op.f("ix_dataset_versions_dataset_id"), "dataset_versions", ["dataset_id"])
    op.create_index(
        op.f("ix_dataset_versions_schema_signature"), "dataset_versions", ["schema_signature"]
    )
    op.execute(
        """
        INSERT INTO dataset_versions (
            id, dataset_id, version_number, original_filename, storage_path, file_format,
            file_size_bytes, sha256_hash, row_count, column_count, processing_status,
            ingestion_started_at, ingestion_completed_at, created_at
        )
        SELECT
            id, id, 1,
            COALESCE(original_filename, name),
            COALESCE(file_path, 'legacy'),
            'csv',
            COALESCE(file_size_bytes, 0),
            COALESCE(file_hash, repeat('0', 64)),
            row_count,
            column_count,
            CASE WHEN status = 'metadata_failed' THEN 'metadata_failed' ELSE 'completed' END,
            created_at,
            updated_at,
            created_at
        FROM datasets
        """
    )
    op.execute("UPDATE datasets SET current_version_id = id WHERE current_version_id IS NULL")
    op.create_foreign_key(
        "fk_datasets_current_version_id",
        "datasets",
        "dataset_versions",
        ["current_version_id"],
        ["id"],
        use_alter=True,
    )

    op.create_table(
        "dataset_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_rows", sa.BigInteger(), nullable=False),
        sa.Column("total_columns", sa.Integer(), nullable=False),
        sa.Column("duplicate_row_count", sa.BigInteger(), nullable=False),
        sa.Column("duplicate_row_percentage", sa.Float(), nullable=False),
        sa.Column("fully_null_row_count", sa.BigInteger(), nullable=False),
        sa.Column("estimated_memory_bytes", sa.BigInteger(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("execution_duration_ms", sa.Float(), nullable=False),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"], ["dataset_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_version_id", name="uq_dataset_profiles_version"),
    )
    op.create_index(
        op.f("ix_dataset_profiles_dataset_version_id"), "dataset_profiles", ["dataset_version_id"]
    )

    op.add_column(
        "dataset_columns",
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("dataset_columns", sa.Column("logical_type", sa.String(length=50), nullable=True))
    op.add_column(
        "dataset_columns", sa.Column("physical_type", sa.String(length=100), nullable=True)
    )
    op.add_column("dataset_columns", sa.Column("non_null_count", sa.BigInteger(), nullable=True))
    op.add_column("dataset_columns", sa.Column("distinct_count", sa.BigInteger(), nullable=True))
    op.add_column("dataset_columns", sa.Column("median_value", sa.Float(), nullable=True))
    op.add_column("dataset_columns", sa.Column("stddev_value", sa.Float(), nullable=True))
    op.add_column("dataset_columns", sa.Column("min_length", sa.Integer(), nullable=True))
    op.add_column("dataset_columns", sa.Column("max_length", sa.Integer(), nullable=True))
    op.add_column("dataset_columns", sa.Column("avg_length", sa.Float(), nullable=True))
    op.add_column(
        "dataset_columns", sa.Column("earliest_value", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "dataset_columns", sa.Column("latest_value", sa.String(length=255), nullable=True)
    )
    op.add_column("dataset_columns", sa.Column("is_constant", sa.Boolean(), nullable=True))
    op.add_column("dataset_columns", sa.Column("is_fully_null", sa.Boolean(), nullable=True))
    op.add_column("dataset_columns", sa.Column("is_high_null", sa.Boolean(), nullable=True))
    op.add_column(
        "dataset_columns", sa.Column("is_candidate_identifier", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "dataset_columns", sa.Column("is_possible_categorical", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "dataset_columns", sa.Column("is_possible_datetime_text", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "dataset_columns", sa.Column("is_possible_numeric_text", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "dataset_columns",
        sa.Column("top_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute(
        """
        UPDATE dataset_columns AS c
        SET
            dataset_version_id = d.current_version_id,
            logical_type = CASE
                WHEN c.inferred_data_type ILIKE '%int%' THEN 'integer'
                WHEN c.inferred_data_type ILIKE '%float%' THEN 'decimal'
                WHEN c.inferred_data_type ILIKE '%bool%' THEN 'boolean'
                WHEN c.inferred_data_type ILIKE '%date%' THEN 'datetime'
                WHEN c.inferred_data_type ILIKE '%object%' THEN 'string'
                ELSE 'unknown'
            END,
            physical_type = c.inferred_data_type,
            non_null_count = GREATEST(COALESCE(d.row_count, 0) - c.null_count, 0),
            distinct_count = c.unique_count,
            is_constant = c.unique_count = 1,
            is_fully_null =
                COALESCE(d.row_count, 0) > 0
                AND c.null_count = COALESCE(d.row_count, 0),
            is_high_null = c.null_percentage >= 40,
            is_candidate_identifier = c.null_count = 0 AND c.unique_percentage >= 98,
            is_possible_categorical = c.unique_percentage <= 5,
            is_possible_datetime_text = false,
            is_possible_numeric_text = false,
            top_values = '[]'::jsonb
        FROM datasets AS d
        WHERE c.dataset_id = d.id
        """
    )
    op.alter_column("dataset_columns", "null_count", type_=sa.BigInteger(), existing_nullable=False)
    for column_name in (
        "dataset_version_id",
        "logical_type",
        "physical_type",
        "non_null_count",
        "distinct_count",
        "is_constant",
        "is_fully_null",
        "is_high_null",
        "is_candidate_identifier",
        "is_possible_categorical",
        "is_possible_datetime_text",
        "is_possible_numeric_text",
        "top_values",
    ):
        op.alter_column("dataset_columns", column_name, nullable=False)
    op.drop_index("ix_dataset_columns_dataset_id", table_name="dataset_columns")
    op.drop_constraint("dataset_columns_dataset_id_fkey", "dataset_columns", type_="foreignkey")
    op.drop_column("dataset_columns", "dataset_id")
    op.drop_column("dataset_columns", "inferred_data_type")
    op.drop_column("dataset_columns", "unique_count")
    op.create_index(
        op.f("ix_dataset_columns_dataset_version_id"),
        "dataset_columns",
        ["dataset_version_id"],
    )
    op.create_unique_constraint(
        "uq_dataset_columns_version_name",
        "dataset_columns",
        ["dataset_version_id", "column_name"],
    )
    op.create_unique_constraint(
        "uq_dataset_columns_version_position",
        "dataset_columns",
        ["dataset_version_id", "column_position"],
    )
    op.create_foreign_key(
        None,
        "dataset_columns",
        "dataset_versions",
        ["dataset_version_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "data_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("previous_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["previous_version_id"], ["data_contracts.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "version", name="uq_data_contracts_dataset_version"),
    )
    op.create_index("ix_data_contracts_dataset_active", "data_contracts", ["dataset_id", "active"])
    op.create_index(op.f("ix_data_contracts_dataset_id"), "data_contracts", ["dataset_id"])

    op.create_table(
        "dataset_version_comparisons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("base_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comparison_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_status", sa.String(length=30), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["base_version_id"], ["dataset_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["comparison_version_id"], ["dataset_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_comparisons_versions",
        "dataset_version_comparisons",
        ["base_version_id", "comparison_version_id"],
    )
    op.create_index(
        op.f("ix_dataset_version_comparisons_dataset_id"),
        "dataset_version_comparisons",
        ["dataset_id"],
    )

    op.create_table(
        "validation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contract_version", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_rows", sa.BigInteger(), nullable=False),
        sa.Column("valid_rows", sa.BigInteger(), nullable=False),
        sa.Column("invalid_rows", sa.BigInteger(), nullable=False),
        sa.Column("passed_rules", sa.Integer(), nullable=False),
        sa.Column("failed_rules", sa.Integer(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("score_components", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("accepted_output_path", sa.String(length=1024), nullable=True),
        sa.Column("quarantine_output_path", sa.String(length=1024), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["contract_id"], ["data_contracts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"], ["dataset_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_validation_runs_dataset_id"), "validation_runs", ["dataset_id"])
    op.create_index(
        op.f("ix_validation_runs_dataset_version_id"), "validation_runs", ["dataset_version_id"]
    )
    op.create_index(
        "ix_validation_runs_version_created",
        "validation_runs",
        ["dataset_version_id", "created_at"],
    )

    op.create_table(
        "quarantined_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_row_number", sa.BigInteger(), nullable=False),
        sa.Column("row_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("failed_rule_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("failure_messages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "quarantined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"], ["dataset_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["validation_run_id"], ["validation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_quarantined_rows_validation_run_id"), "quarantined_rows", ["validation_run_id"]
    )

    op.create_table(
        "validation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_code", sa.String(length=255), nullable=False),
        sa.Column("rule_type", sa.String(length=100), nullable=False),
        sa.Column("column_name", sa.String(length=255), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("evaluated_count", sa.BigInteger(), nullable=False),
        sa.Column("failure_count", sa.BigInteger(), nullable=False),
        sa.Column("failure_percentage", sa.Float(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["validation_run_id"], ["validation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_validation_results_run_status", "validation_results", ["validation_run_id", "status"]
    )
    op.create_index(
        op.f("ix_validation_results_validation_run_id"), "validation_results", ["validation_run_id"]
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is intentionally not supported for schema sync migration.")
