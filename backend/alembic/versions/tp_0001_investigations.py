"""Store versioned Turning Point investigations and their reviews."""

import sqlalchemy as sa
from alembic import op

revision = "tp_0001"
down_revision = "20260725_0005"


def upgrade() -> None:
    op.create_table(
        "turning_point_investigations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("case_id", sa.String(64), nullable=False),
        sa.Column("source_version", sa.String(16), nullable=False),
        sa.Column("claim", sa.String(400), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("turning_point_investigations.id")),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_turning_point_investigations_parent_id", "turning_point_investigations", ["parent_id"]
    )


def downgrade() -> None:
    op.drop_table("turning_point_investigations")
