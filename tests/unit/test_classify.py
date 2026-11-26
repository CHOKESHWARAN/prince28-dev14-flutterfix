"""Unit tests for the question router (classify.py) and test set."""

import json
from pathlib import Path

import pytest

from flutterfix.llm.classify import (
    LABELS,
    accuracy,
    build_messages,
    classify,
    find_leaks,
    parse_label,
)
from flutterfix.llm.gateway import FakeLLM, LLMGateway
from flutterfix.llm.prompts import find_prompts


def test_parse_label_normalizes_valid_labels():
    assert parse_label("docs") == "docs"
    assert parse_label("DOCS.") == "docs"
    assert parse_label("The answer is docs.") == "docs"
    assert parse_label("personal") == "personal"
    assert parse_label("Personal.") == "personal"
    assert parse_label("off_topic") == "off_topic"
    assert parse_label("off-topic") == "off_topic"
    assert parse_label("Off-Topic.") == "off_topic"


def test_parse_label_rejects_ambiguity_and_missing():
    assert parse_label("docs or personal") == "invalid"
    assert parse_label("both off_topic and docs") == "invalid"
    assert parse_label("I am not sure") == "invalid"
    assert parse_label("") == "invalid"


def test_build_messages_wraps_in_tags():
    msgs = build_messages("System prompt text", "How do I migrate FlatButton?")
    assert len(msgs) == 2
    assert msgs[0] == {"role": "system", "content": "System prompt text"}
    assert msgs[1]["role"] == "user"
    assert "<question>\nHow do I migrate FlatButton?\n</question>" in msgs[1]["content"]


@pytest.mark.anyio
async def test_classify_calls_gateway_and_parses_label():
    fake = FakeLLM(name="gemini", script=["docs."])
    gateway = LLMGateway([fake])
    label, result = await classify(gateway, "System prompt", "classify_v1", "What is Widget?")
    assert label == "docs"
    assert result.text == "docs."


def test_accuracy_calculation():
    rows = [
        {"label": "docs", "got": "docs"},
        {"label": "personal", "got": "personal"},
        {"label": "off_topic", "got": "docs"},
        {"label": "personal", "got": "invalid"},
    ]
    assert accuracy(rows) == 0.5
    assert accuracy([]) == 0.0


def test_find_leaks_detects_prompt_overlap():
    prompt = "Here is an example: What is Widget? docs"
    questions = ["What is Widget?", "How to run app?"]
    leaks = find_leaks(prompt, questions)
    assert leaks == ["What is Widget?"]


def test_repo_prompt_files_and_testset():
    prompts = find_prompts("classify", directory="prompts")
    assert len(prompts) >= 3, f"Expected at least 3 classify prompts, found: {list(prompts.keys())}"

    testset_file = Path("eval/prompt_testset.jsonl")
    assert testset_file.is_file(), "eval/prompt_testset.jsonl does not exist"

    lines = [
        line.strip()
        for line in testset_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) >= 20, f"Expected at least 20 test questions, found {len(lines)}"

    questions = []
    for idx, line in enumerate(lines, 1):
        assert "TODO" not in line, f"Line {idx} still contains TODO: {line}"
        data = json.loads(line)
        assert "question" in data and "label" in data
        assert data["label"] in LABELS, f"Invalid label '{data['label']}' at line {idx}"
        questions.append(data["question"])

    v3_content = prompts.get("classify_v3", "")
    assert v3_content, "classify_v3.md not found"
    leaks = find_leaks(v3_content, questions)
    assert not leaks, f"classify_v3.md leaks test questions: {leaks}"
