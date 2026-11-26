"""add llm_calls

Revision ID: 0004_add_llm_calls
Revises: 0003_add_index_on_doc_type
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_add_llm_calls"
down_revision: str | Sequence[str] | None = "0003_add_index_on_doc_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("purpose", sa.String(40), server_default="chat", nullable=False),
        sa.Column("prompt_version", sa.String(80), server_default="", nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("error", sa.Text(), server_default="", nullable=False),
        sa.Column("tokens_in", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tokens_out", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_inr", sa.Numeric(12, 6), server_default="0", nullable=False),
        sa.Column("fallback_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_llm_calls_request_id", "llm_calls", ["request_id"])
    op.create_index("ix_llm_calls_created_at", "llm_calls", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_calls_created_at", table_name="llm_calls")
    op.drop_index("ix_llm_calls_request_id", table_name="llm_calls")
    op.drop_table("llm_calls")
