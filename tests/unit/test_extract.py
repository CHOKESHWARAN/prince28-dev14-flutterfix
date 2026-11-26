"""Unit tests for structured metadata extraction (extract.py and DocMeta)."""

import pytest
from pydantic import ValidationError

from flutterfix.llm.doc_meta import DocMeta
from flutterfix.llm.extract import explain, extract, parse_json
from flutterfix.llm.gateway import FakeLLM, LLMGateway
from flutterfix.llm.prompts import load_prompt


def test_parse_json_handles_fences_and_extra_text():
    raw = (
        'Here is the JSON:\n```json\n{"summary": "Test summary", "doc_kind": "guide"}\n```\n'
        "Hope that helps!"
    )
    assert parse_json(raw) == {"summary": "Test summary", "doc_kind": "guide"}

    bare = '{"summary": "Bare JSON"}'
    assert parse_json(bare) == {"summary": "Bare JSON"}


def test_parse_json_raises_on_missing_or_invalid():
    with pytest.raises(ValueError, match="no JSON object"):
        parse_json("No json here at all.")
    with pytest.raises(ValueError):
        parse_json("{invalid json object}")


def test_explain_formats_validation_errors():
    try:
        DocMeta.model_validate({"doc_kind": "invalid_kind"})
    except ValidationError as err:
        msg = explain(err)
        assert "doc_kind" in msg or "summary" in msg


def test_doc_meta_is_a_strict_contract():
    data = {
        "doc_kind": "guideline",
        "year": 2024,
        "language": "en",
        "summary": "A guide on migrating Flutter buttons to latest standards.",
        "topics": ["Flutter", "MIGRATION", "flutter"],
        "page": ["Buttons"],
        "widget_or_api": ["FlatButton", "TextButton"],
        "flutter_version": ["3.24"],
        "dart_version": ["3.5"],
        "change_type": ["deprecation"],
    }
    meta = DocMeta.model_validate(data)
    # topics tidied: lowercased and deduplicated
    assert meta.topics == ["flutter", "migration"]

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        DocMeta.model_validate({**data, "unexpected_field": "bad"})


def test_doc_meta_year_and_summary_constraints():
    base = {
        "doc_kind": "tutorial",
        "language": "en",
        "summary": "Valid summary of adequate length for testing.",
        "topics": ["widgets"],
        "page": [],
        "widget_or_api": [],
        "flutter_version": [],
        "dart_version": [],
        "change_type": [],
    }
    # Year boundaries: 1950 <= year <= 2027
    DocMeta.model_validate({**base, "year": 2026})
    with pytest.raises(ValidationError):
        DocMeta.model_validate({**base, "year": 1940})
    with pytest.raises(ValidationError):
        DocMeta.model_validate({**base, "year": 2030})

    # Summary too short (<20 chars)
    with pytest.raises(ValidationError):
        DocMeta.model_validate({**base, "summary": "Too short"})


def test_prompt_mentions_all_doc_meta_fields():
    prompt = load_prompt("extract", 1, directory="prompts")
    for field_name in DocMeta.model_fields:
        assert field_name in prompt, (
            f"Prompt extract_v1.md does not mention DocMeta field: {field_name!r}"
        )


@pytest.mark.anyio
async def test_extract_retries_on_validation_failure_and_repairs():
    valid_json = (
        '{"doc_kind": "guideline", "year": 2024, "language": "en", '
        '"summary": "A complete guide on migrating buttons in Flutter.", '
        '"topics": ["migration"], "page": [], "widget_or_api": ["TextButton"], '
        '"flutter_version": ["3.24"], "dart_version": [], "change_type": ["deprecation"]}'
    )
    fake = FakeLLM(name="gemini", script=['{"doc_kind": "bad"}', valid_json])
    gw = LLMGateway([fake])

    res = await extract(gw, DocMeta, "Prompt", "extract_v1", "Doc Title", "Doc Text")
    assert res.record is not None
    assert res.attempts == 2
    assert len(res.errors) == 1
    assert res.record.doc_kind == "guideline"


@pytest.mark.anyio
async def test_extract_marks_failed_after_max_attempts():
    fake = FakeLLM(name="gemini", script=['{"doc_kind": "bad"}'] * 3)
    gw = LLMGateway([fake])

    res = await extract(
        gw, DocMeta, "Prompt", "extract_v1", "Doc Title", "Doc Text", max_attempts=3
    )
    assert res.record is None
    assert res.attempts == 3
    assert len(res.errors) == 3
