"""add ingest_jobs and ingest_items

Revision ID: 0006_add_ingest_jobs
Revises: 0005_add_llm_calls
Create Date: 2026-11-27 14:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_add_ingest_jobs"
down_revision: str | Sequence[str] | None = "0005_add_llm_calls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingest_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("requested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingest_jobs")),
    )
    op.create_table(
        "ingest_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("record", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["ingest_jobs.id"],
            name=op.f("fk_ingest_items_job_id_ingest_jobs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingest_items")),
    )
    op.create_index(op.f("ix_ingest_items_job_id"), "ingest_items", ["job_id"], unique=False)
    op.create_index(op.f("ix_ingest_items_status"), "ingest_items", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ingest_items_status"), table_name="ingest_items")
    op.drop_index(op.f("ix_ingest_items_job_id"), table_name="ingest_items")
    op.drop_table("ingest_items")
    op.drop_table("ingest_jobs")
