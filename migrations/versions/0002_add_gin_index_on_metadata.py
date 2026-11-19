"""add gin index on metadata

Revision ID: 0002_add_gin_index_on_metadata
Revises: 0001_create_documents_and_pages
Create Date: 2026-11-19 10:15:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_add_gin_index_on_metadata"
down_revision: str | Sequence[str] | None = "0001_create_documents_and_pages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_documents_metadata_gin",
        "documents",
        ["metadata"],
        postgresql_using="gin",
        postgresql_ops={"metadata": "jsonb_path_ops"},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_documents_metadata_gin",
        table_name="documents",
        postgresql_using="gin",
    )
