"""SQLAlchemy declarative models for FlutterFix PostgreSQL database."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Predictable naming convention for database constraints and indexes
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = metadata


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    licence: Mapped[str | None] = mapped_column(String(200), nullable=True)
    doc_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="breaking_change", index=True
    )
    published_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    pages: Mapped[list["Page"]] = relationship(
        "Page",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def license(self) -> str | None:
        return self.licence

    @license.setter
    def license(self, val: str | None) -> None:
        self.licence = val


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (
        CheckConstraint("page_no >= 1", name="page_no_positive"),
        UniqueConstraint("document_id", "page_no", name="uq_pages_document_id_page_no"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    document: Mapped["Document"] = relationship("Document", back_populates="pages")

    @property
    def content(self) -> str:
        return self.text

    @content.setter
    def content(self, val: str) -> None:
        self.text = val

    @property
    def url(self) -> str | None:
        return self.document.source_url if self.document else None

    @property
    def title(self) -> str | None:
        return self.document.title if self.document else None


# Note: GIN index 'ix_documents_metadata_gin' on documents.metadata is added in Migration 2.
gin_index = Index(
    "ix_documents_metadata_gin",
    Document.metadata_,
    postgresql_using="gin",
    postgresql_ops={"metadata": "jsonb_path_ops"},
)
