"""Integration test for saving extracted metadata to PostgreSQL."""

from flutterfix.config import Settings
from flutterfix.db.models import Document
from flutterfix.db.session import make_engine, make_sessionmaker
from flutterfix.llm.doc_meta import DocMeta
from flutterfix.llm.extract import Extraction, save


async def test_save_extracted_metadata_to_document(database_url):
    engine = make_engine(Settings(app_env="ci", database_url=database_url, _env_file=None))
    sessionmaker = make_sessionmaker(engine)

    async with sessionmaker() as session:
        doc = Document(
            external_id="test-doc-extract-1",
            title="Test Doc for Extraction",
            doc_type="html",
            metadata_={"source": "test", "chars": 500},
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        meta = DocMeta(
            doc_kind="tutorial",
            year=2024,
            language="en",
            summary="A comprehensive test guide for metadata extraction.",
            topics=["testing", "extraction"],
            page=["Introduction"],
            widget_or_api=["Widget"],
            flutter_version=["3.24"],
            dart_version=["3.5"],
            change_type=["feature"],
        )
        extraction = Extraction(
            record=meta,
            attempts=1,
            model="test-model",
            tokens_in=50,
            tokens_out=30,
            cost_inr=0.01,
        )
        await save(session, doc, extraction, "extract_v1")

        await session.refresh(doc)
        assert doc.metadata_["doc_kind"] == "tutorial"
        assert doc.metadata_["year"] == 2024
        assert doc.metadata_["extract"]["prompt"] == "extract_v1"
        assert doc.metadata_["extract"]["model"] == "test-model"

        # Clean up
        await session.delete(doc)
        await session.commit()

    await engine.dispose()
