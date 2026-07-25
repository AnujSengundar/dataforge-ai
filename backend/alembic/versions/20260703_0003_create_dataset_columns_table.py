"""create dataset columns table

Revision ID: 20260703_0003
Revises: 759fa358b89a
Create Date: 2026-07-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260703_0003"
down_revision: str | Sequence[str] | None = "759fa358b89a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dataset_columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("column_name", sa.String(length=255), nullable=False),
        sa.Column("column_position", sa.Integer(), nullable=False),
        sa.Column("inferred_data_type", sa.String(length=100), nullable=False),
        sa.Column("nullable", sa.Boolean(), nullable=False),
        sa.Column("null_count", sa.Integer(), nullable=False),
        sa.Column("null_percentage", sa.Float(), nullable=False),
        sa.Column("unique_count", sa.Integer(), nullable=False),
        sa.Column("unique_percentage", sa.Float(), nullable=False),
        sa.Column("sample_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("min_value", sa.String(length=255), nullable=True),
        sa.Column("max_value", sa.String(length=255), nullable=True),
        sa.Column("mean_value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dataset_columns_dataset_id"), "dataset_columns", ["dataset_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_dataset_columns_dataset_id"), table_name="dataset_columns")
    op.drop_table("dataset_columns")
