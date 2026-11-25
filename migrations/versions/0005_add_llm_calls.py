"""add llm_calls

Revision ID: 0005_add_llm_calls
Revises: 0004_add_page_headings_and_parse_failures
Create Date: 2026-11-25 12:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_add_llm_calls"
down_revision: str | Sequence[str] | None = "0004_add_page_headings_and_parse_failures"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("purpose", sa.String(length=40), server_default="chat", nullable=False),
        sa.Column("prompt_version", sa.String(length=80), server_default="", nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("error", sa.Text(), server_default="", nullable=False),
        sa.Column("tokens_in", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tokens_out", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "cost_inr", sa.Numeric(precision=12, scale=6), server_default="0", nullable=False
        ),
        sa.Column("fallback_used", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_llm_calls_created_at"),
        "llm_calls",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_llm_calls_request_id"),
        "llm_calls",
        ["request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_calls_request_id"), table_name="llm_calls")
    op.drop_index(op.f("ix_llm_calls_created_at"), table_name="llm_calls")
    op.drop_table("llm_calls")
