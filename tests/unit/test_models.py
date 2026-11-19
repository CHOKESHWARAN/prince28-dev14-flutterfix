from datetime import date

from flutterfix.db.models import NAMING_CONVENTION, Base, Document, Page


def test_naming_convention():
    assert "ix" in NAMING_CONVENTION
    assert "uq" in NAMING_CONVENTION
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"


def test_document_model_fields_and_properties():
    doc = Document(
        external_id="doc-123",
        title="Flutter Migration Guide",
        source_url="https://docs.flutter.dev/release/breaking-changes",
        licence="CC-BY-4.0",
        doc_type="guide",
        published_on=date(2024, 1, 15),
        sha256="abc123sha256",
        metadata_={"category": "core", "flutter_version": "3.19"},
    )

    assert doc.external_id == "doc-123"
    assert doc.title == "Flutter Migration Guide"
    assert doc.source_url == "https://docs.flutter.dev/release/breaking-changes"
    assert doc.licence == "CC-BY-4.0"
    assert doc.license == "CC-BY-4.0"
    assert doc.doc_type == "guide"
    assert doc.published_on == date(2024, 1, 15)
    assert doc.sha256 == "abc123sha256"
    assert doc.metadata_["category"] == "core"

    # Test setter alias
    doc.license = "Apache-2.0"
    assert doc.licence == "Apache-2.0"
    assert doc.license == "Apache-2.0"


def test_page_model_and_relationship():
    doc = Document(
        external_id="doc-456",
        title="Widget Guide",
        source_url="https://docs.flutter.dev/widgets",
        licence="CC-BY-4.0",
        doc_type="widget",
        sha256="xyz456sha256",
        metadata_={"category": "widget"},
    )
    page = Page(page_no=1, text="Page 1 body content")
    doc.pages.append(page)

    assert len(doc.pages) == 1
    assert page.page_no == 1
    assert page.text == "Page 1 body content"
    assert page.content == "Page 1 body content"
    assert page.document == doc
    assert page.url == "https://docs.flutter.dev/widgets"
    assert page.title == "Widget Guide"

    # Test content setter
    page.content = "Updated content"
    assert page.text == "Updated content"
