"""Extract structured metadata for every parsed document in Postgres.

Usage:
    uv run python scripts/extract_metadata.py
    uv run python scripts/extract_metadata.py --limit 5
    uv run python scripts/extract_metadata.py --retry-failed
"""

import argparse
import asyncio
import time

from flutterfix.config import get_settings
from flutterfix.db.session import make_engine, make_sessionmaker
from flutterfix.llm.doc_meta import DocMeta
from flutterfix.llm.extract import run
from flutterfix.llm.gateway import build_gateway
from flutterfix.llm.prompts import latest_prompt


async def main() -> None:
    parser = argparse.ArgumentParser(description="Extract document metadata using LLM")
    parser.add_argument("--limit", type=int, default=0, help="Max documents to process")
    parser.add_argument("--rpm", type=float, default=12.0, help="Requests per minute")
    parser.add_argument("--chars", type=int, default=6000, help="Max text characters per document")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed extractions")
    parser.add_argument(
        "--native", action="store_true", help="Use native response_format json_schema"
    )
    args = parser.parse_args()

    settings = get_settings()
    engine = make_engine(settings)
    sessionmaker = make_sessionmaker(engine)
    gateway = build_gateway(settings)

    version, prompt = latest_prompt("extract", directory="prompts")
    started = time.perf_counter()

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
