"""EXPLAIN ANALYZE demonstration for JSONB metadata queries and GIN index verification."""

import asyncio
import json
import sys

from sqlalchemy import text

from flutterfix.db.session import dispose_engine, engine


async def run_explain_analyze() -> None:
    query = text(
        "EXPLAIN (ANALYZE, BUFFERS) "
        "SELECT id, external_id, title FROM documents "
        "WHERE metadata @> CAST(:f AS jsonb)"
    )
    param = {"f": json.dumps({"category": "widget"})}

    async with engine.connect() as conn:
        print("=" * 70)
        print("1. NORMAL QUERY PLAN (enable_seqscan = on)")
        print("=" * 70)
        result1 = await conn.execute(query, param)
        plan1_lines = [row[0] for row in result1.fetchall()]
        print("\n".join(plan1_lines))

        print("\n" + "=" * 70)
        print("2. FORCED INDEX SCAN PLAN (enable_seqscan = off)")
        print("=" * 70)
        await conn.execute(text("SET enable_seqscan = off"))
        result2 = await conn.execute(query, param)
        plan2_lines = [row[0] for row in result2.fetchall()]
        print("\n".join(plan2_lines))

        # Reset setting
        await conn.execute(text("SET enable_seqscan = on"))

        # Verify GIN index usage in plan 2
        gin_used = any("ix_documents_metadata_gin" in line for line in plan2_lines)
        print("\n" + "=" * 70)
        print(f"Index 'ix_documents_metadata_gin' utilized in plan 2: {gin_used}")
        print("=" * 70)


async def main() -> int:
    try:
        await run_explain_analyze()
        return 0
    except Exception as exc:
        print(f"EXPLAIN ANALYZE failed: {exc}", file=sys.stderr)
        return 1
    finally:
        await dispose_engine()


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
