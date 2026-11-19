"""create documents and pages

Revision ID: 0001_create_documents_and_pages
Revises:
Create Date: 2026-11-19 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_create_documents_and_pages"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("licence", sa.String(length=200), nullable=True),
        sa.Column(
            "doc_type", sa.String(length=50), nullable=False, server_default="breaking_change"
        ),
        sa.Column("published_on", sa.Date(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.UniqueConstraint("external_id", name="uq_documents_external_id"),
    )
    op.create_index("ix_documents_external_id", "documents", ["external_id"], unique=True)
    op.create_index("ix_documents_sha256", "documents", ["sha256"], unique=False)

    # Create pages table
    op.create_table(
        "pages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.CheckConstraint("page_no >= 1", name="ck_pages_page_no_positive"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_pages_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pages"),
        sa.UniqueConstraint("document_id", "page_no", name="uq_pages_document_id_page_no"),
    )
    op.create_index("ix_pages_document_id", "pages", ["document_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pages_document_id", table_name="pages")
    op.drop_table("pages")
    op.drop_index("ix_documents_sha256", table_name="documents")
    op.drop_index("ix_documents_external_id", table_name="documents")
    op.drop_table("documents")
