"""add index on doc_type

Revision ID: 0003_add_index_on_doc_type
Revises: 0002_add_gin_index_on_metadata
Create Date: 2026-11-19 18:45:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_add_index_on_doc_type"
down_revision: str | Sequence[str] | None = "0002_add_gin_index_on_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_documents_doc_type",
        "documents",
        ["doc_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_documents_doc_type",
        table_name="documents",
    )
