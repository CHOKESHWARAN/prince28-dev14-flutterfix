"""Compare prompt versions on the 20-question test set.

Caches answers in eval/cache/ so reruns are fast and only call the model for new questions/versions.
Appends or updates the results table in NOTES.md.

Usage:
    uv run python scripts/compare_prompts.py
"""

import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path

from flutterfix.config import get_settings
from flutterfix.llm.classify import (
    accuracy,
    build_messages,
    find_leaks,
    parse_label,
)
from flutterfix.llm.gateway import build_gateway
from flutterfix.llm.prompts import find_prompts

CACHE_DIR = Path("eval/cache")
TESTSET_PATH = Path("eval/prompt_testset.jsonl")
NOTES_PATH = Path("NOTES.md")


def load_testset() -> list[dict]:
    if not TESTSET_PATH.is_file():
        raise FileNotFoundError(f"Test set not found: {TESTSET_PATH}")
    rows = []
    for line in TESTSET_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def cache_key(version: str, question: str) -> Path:
    q_hash = hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{version}_{q_hash}.json"


async def run_comparison(rpm: float = 12.0) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    testset = load_testset()
    questions = [item["question"] for item in testset]

    prompts = find_prompts("classify", directory="prompts")
    if not prompts:
        print("No classify prompts found in prompts/")
        sys.exit(1)

    # Check for leaks
    for ver, content in prompts.items():
        leaks = find_leaks(content, questions)
        if leaks:
            print(f"LEAK in {ver}: {len(leaks)} test questions appear in the prompt! ({leaks})")

    settings = get_settings()
    gateway = build_gateway(settings)

    results_table = []
    calls_made = 0

    print("=" * 60)
    print(f"Evaluating {len(prompts)} prompt versions on {len(testset)} test questions...")
    print("=" * 60)

    for version, prompt_text in prompts.items():
        eval_rows = []
        misses = []
        ver_calls = 0

        for line_no, item in enumerate(testset, start=1):
            question = item["question"]
            expected = item["label"]
            ckey = cache_key(version, question)

            if ckey.is_file():
                try:
                    cached_data = json.loads(ckey.read_text(encoding="utf-8"))
                    reply_text = cached_data.get("reply", "")
                except Exception:
                    reply_text = ""
            else:
                reply_text = ""

            if not reply_text:
                for retry in range(4):
                    try:
                        messages = build_messages(prompt_text, question)
                        res = await gateway.generate(
                            messages,
                            purpose="classify",
                            prompt_version=version,
                            temperature=0,
                        )
                        reply_text = res.text
                        ver_calls += 1
                        calls_made += 1
                        break
                    except Exception as err:
                        if retry < 3:
                            await asyncio.sleep(5)
                            continue
                        print(f"Failed call for {version} line {line_no}: {err}")
                        raise err

                # Save cache
                ckey.write_text(
                    json.dumps(
                        {
                            "reply": reply_text,
                            "model": res.model,
                            "tokens_in": res.tokens_in,
                            "tokens_out": res.tokens_out,
                            "cost_inr": res.cost_inr,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                # Respect rate limits
                await asyncio.sleep(60.0 / rpm)

            parsed = parse_label(reply_text)
            eval_rows.append({"label": expected, "got": parsed})

            if parsed != expected:
                misses.append(f"Line {line_no}")
                short_q = question[:40]
                print(
                    f"{version} missed line {line_no}: wanted {expected}, "
                    f"got {parsed} (reply '{reply_text}') '{short_q}...'"
                )

        score = accuracy(eval_rows)
        correct_count = sum(r["got"] == r["label"] for r in eval_rows)
        pct = int(score * 100)
        print(f"{version} {correct_count}/{len(testset)} {pct}%")

        results_table.append(
            {
                "version": version,
                "score": score,
                "correct": f"{correct_count}/{len(testset)}",
                "pct": f"{pct}%",
                "misses": ", ".join(misses) if misses else "None",
            }
        )

    print(f"model calls made now: {calls_made} (the rest came from the cache) -> table in NOTES.md")
    update_notes_table(results_table)


def update_notes_table(rows: list[dict]) -> None:
    header = "| Version | Accuracy | Correct | Missed questions |\n|---|---|---|---|\n"
    table_lines = [header]
    for r in rows:
        table_lines.append(f"| {r['version']} | {r['pct']} | {r['correct']} | {r['misses']} |\n")
    table_str = "".join(table_lines)

    notes_text = NOTES_PATH.read_text(encoding="utf-8") if NOTES_PATH.is_file() else ""

    # Check if a D09 table section already exists
    marker = "<!-- router_comparison_start -->"
    end_marker = "<!-- router_comparison_end -->"
    section = f"{marker}\n{table_str}{end_marker}\n"

    if marker in notes_text and end_marker in notes_text:
        pattern = re.compile(rf"{re.escape(marker)}.*?{re.escape(end_marker)}\n?", re.DOTALL)
        notes_text = pattern.sub(section, notes_text)
    else:
        # Append before or inside D09 section
        notes_text += f"\n## D09 · Question router accuracy table\n\n{section}"

    NOTES_PATH.write_text(notes_text, encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(run_comparison())
