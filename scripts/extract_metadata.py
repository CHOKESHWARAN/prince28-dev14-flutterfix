"""Extract structured metadata for parsed documents in Postgres or from manifest corpus.

Usage:
    uv run python scripts/extract_metadata.py
    uv run python scripts/extract_metadata.py --limit 50
    uv run python scripts/extract_metadata.py --manifest --limit 50
    uv run python scripts/extract_metadata.py --retry-failed
"""

import argparse
import asyncio
import json
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from flutterfix.config import get_settings
from flutterfix.db.session import make_engine, make_sessionmaker
from flutterfix.ingest.parse import parse_file
from flutterfix.llm.doc_meta import DocMeta
from flutterfix.llm.extract import extract, run
from flutterfix.llm.gateway import LLMGateway, build_gateway
from flutterfix.llm.prompts import latest_prompt

MANIFEST_DEFAULT = Path("data/manifest.jsonl")
OUTPUT_DEFAULT = Path("data/extracted_metadata.jsonl")


async def run_manifest(
    gateway: LLMGateway,
    schema: type[BaseModel],
    prompt: str,
    version: str,
    manifest_path: Path,
    output_path: Path,
    *,
    limit: int = 50,
    rpm: float = 12.0,
    chars: int = 6000,
    retry_failed: bool = False,
    native: bool = False,
    echo: Callable[[str], None] = print,
) -> tuple[Counter, Counter, dict[str, Any]]:
    """Extract metadata directly from manifest-defined parsed corpus files."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    # Load unique downloaded records from manifest
    seen_urls: set[str] = set()
    records: list[dict[str, Any]] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("status") == "downloaded" and Path(item.get("path", "")).is_file():
            url = item.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                records.append(item)

    echo(f"Loaded {len(records)} unique downloaded records from manifest.")

    # Load existing extractions to support resumability
    done_urls: set[str] = set()
    failed_urls: set[str] = set()
    if output_path.exists():
        for line in output_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                url = row.get("source_url")
                extract_note = row.get("metadata", {}).get("extract", {})
                if extract_note.get("prompt") == version:
                    if "error" in extract_note:
                        failed_urls.add(url)
                    else:
                        done_urls.add(url)
            except Exception:
                continue

    todo: list[dict[str, Any]] = []
    for r in records:
        url = r["url"]
        if url in done_urls:
            continue
        if url in failed_urls and not retry_failed:
            continue
        todo.append(r)

    total_selected = len(todo[:limit] if limit else todo)
    echo(f"Selected {total_selected} documents to process (skipped {len(done_urls)} already done).")

    counts: Counter = Counter()
    counts["pending"] = total_selected
    counts["skipped"] = len(done_urls)
    field_counts: Counter = Counter()

    for number, record in enumerate(todo[:limit] if limit else todo, start=1):
        path = Path(record["path"])
        url = record["url"]
        parsed = await asyncio.to_thread(parse_file, path)
        title = parsed.title or record.get("title") or path.stem
        text = "\n\n".join(p.text for p in parsed.pages[:3])[:chars]

        label = f"[{number}/{total_selected}] {path.name} ({title[:40]})"
        echo(f"Processing {label}...")

        result = await extract(gateway, schema, prompt, version, title, text, native_schema=native)
        counts["tokens_in"] += result.tokens_in
        counts["tokens_out"] += result.tokens_out
        counts["micro_inr"] += round(result.cost_inr * 1_000_000)

        record_out: dict[str, Any] = {
            "id": f"f-{record['sha256'][:20]}",
            "sha256": record["sha256"],
            "source_url": url,
            "title": title,
            "path": str(path),
            "doc_type": parsed.kind,
            "metadata": {
                "source": record.get("source", "flutter-docs"),
                "path": str(path),
                "parser": parsed.parser,
                "pages": len(parsed.pages),
                "chars": len(text),
                **(result.record.model_dump(mode="json") if result.record else {}),
                "extract": {
                    "prompt": version,
                    "model": result.model,
                    "attempts": result.attempts,
                    **({"error": result.errors[-1][:300]} if result.record is None else {}),
                },
            },
        }

        # Append immediately for fault tolerance
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "a", encoding="utf-8") as out_f:
            out_f.write(json.dumps(record_out, ensure_ascii=False) + "\n")

        if result.record is None:
            counts["failed"] += 1
            echo(f"  FAILED: {result.errors[-1][:80]}")
        else:
            counts["ok"] += 1
            if result.attempts > 1:
                counts["repaired"] += 1
                echo(f"  Repaired on attempt {result.attempts}: {result.errors[0][:80]}")
            else:
                echo(f"  OK (kind={result.record.doc_kind}, year={result.record.year})")

            # Track extracted fields
            data_dict = result.record.model_dump(mode="json")
            for k, val in data_dict.items():
                if val is not None and val != [] and val != "":
                    field_counts[k] += 1

        if number < total_selected:
            await asyncio.sleep(60 / rpm)

    return counts, field_counts, {"total_corpus": len(records), "output": str(output_path)}


async def main() -> None:
    parser = argparse.ArgumentParser(description="Extract document metadata using LLM")
    parser.add_argument("--limit", type=int, default=0, help="Max documents to process")
    parser.add_argument("--rpm", type=float, default=12.0, help="Requests per minute")
    parser.add_argument("--chars", type=int, default=6000, help="Max text characters per document")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed extractions")
    parser.add_argument(
        "--native", action="store_true", help="Use native response_format json_schema"
    )
    parser.add_argument(
        "--manifest",
        nargs="?",
        const=str(MANIFEST_DEFAULT),
        default="",
        help="Path to manifest.jsonl to run extraction directly on corpus",
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_DEFAULT),
        help="Path to output extracted metadata file",
    )
    args = parser.parse_args()

    settings = get_settings()
    gateway = build_gateway(settings)
    version, prompt = latest_prompt("extract", directory="prompts")
    started = time.perf_counter()

    use_manifest = bool(args.manifest)
    if not use_manifest:
        # Check if database is reachable
        try:
            engine = make_engine(settings)
            sessionmaker = make_sessionmaker(engine)
            async with sessionmaker() as session:
                from sqlalchemy import text

                await session.execute(text("SELECT 1"))
        except Exception as exc:
            print(f"[Notice] Database unreachable ({type(exc).__name__}: {exc}).")
            print("Falling back to parsed corpus from manifest: data/manifest.jsonl")
            use_manifest = True

    if use_manifest:
        manifest_path = Path(args.manifest or MANIFEST_DEFAULT)
        output_path = Path(args.output)
        counts, field_counts, info = await run_manifest(
            gateway,
            DocMeta,
            prompt,
            version,
            manifest_path,
            output_path,
            limit=args.limit,
            rpm=args.rpm,
            chars=args.chars,
            retry_failed=args.retry_failed,
            native=args.native,
        )
        seconds = int(time.perf_counter() - started)
        cost = counts["micro_inr"] / 1_000_000
        print("=" * 60)
        print("CORPUS METADATA EXTRACTION REPORT")
        print(f"Corpus denominator: {info['total_corpus']}")
        print(f"Prompt version:     {version}")
        print(f"Selected / Pending: {counts['pending']}")
        print(f"Skipped (done):     {counts['skipped']}")
        print(f"Successful (ok):    {counts['ok']}")
        print(f"Repaired:           {counts['repaired']}")
        print(f"Failed:             {counts['failed']}")
        print(f"Tokens In / Out:    {counts['tokens_in']} / {counts['tokens_out']}")
        print(f"Total Cost:         Rs {cost:.4f}")
        print(f"Elapsed Time:       {seconds}s")
        print("Extracted Field Counts:")
        for field_name, cnt in sorted(field_counts.items()):
            print(f"  {field_name:<16}: {cnt}")
        print(f"Output saved to:    {info['output']}")
        print("=" * 60)
    else:
        counts = await run(
            sessionmaker,
            gateway,
            DocMeta,
            prompt,
            version,
            limit=args.limit,
            rpm=args.rpm,
            chars=args.chars,
            retry_failed=args.retry_failed,
            native=args.native,
        )
        seconds = int(time.perf_counter() - started)
        cost = counts["micro_inr"] / 1_000_000
        print(
            f"prompt={version} pending={counts['pending']} ok={counts['ok']} "
            f"repaired={counts['repaired']} failed={counts['failed']} "
            f"tokens_in={counts['tokens_in']} tokens_out={counts['tokens_out']} "
            f"cost=Rs {cost:.4f} seconds={seconds}"
        )


if __name__ == "__main__":
    asyncio.run(main())
