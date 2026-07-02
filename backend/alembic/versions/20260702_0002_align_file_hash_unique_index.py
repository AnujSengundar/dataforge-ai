"""align file hash unique index

Revision ID: 20260702_0002
Revises: 20260702_0001
Create Date: 2026-07-02
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260702_0002"
down_revision: str | Sequence[str] | None = "20260702_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("datasets_file_hash_key", "datasets", type_="unique")
    op.drop_index(op.f("ix_datasets_file_hash"), table_name="datasets")
    op.create_index(op.f("ix_datasets_file_hash"), "datasets", ["file_hash"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_datasets_file_hash"), table_name="datasets")
    op.create_index(op.f("ix_datasets_file_hash"), "datasets", ["file_hash"], unique=False)
    op.create_unique_constraint("datasets_file_hash_key", "datasets", ["file_hash"])
