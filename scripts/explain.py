"""EXPLAIN ANALYZE demonstration for JSONB metadata queries and GIN index verification."""

import argparse
import asyncio
import json
import sys

from sqlalchemy import text

from flutterfix.db.session import dispose_engine, engine


async def run_explain_analyze(filter_field: str = "category", filter_value: str = "widget") -> None:
    query = text(
        "EXPLAIN (ANALYZE, BUFFERS) "
        "SELECT id, external_id, title FROM documents "
        "WHERE metadata @> CAST(:f AS jsonb)"
    )
    param = {"f": json.dumps({filter_field: filter_value})}

    async with engine.connect() as conn:
        print("=" * 70)
        print(f"QUERY: metadata @> '{json.dumps({filter_field: filter_value})}'")
        print("=" * 70)

        print("\n" + "=" * 70)
        print("1. NORMAL QUERY PLAN (enable_seqscan = on, default PostgreSQL optimizer)")
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
        print(f"GIN Index 'ix_documents_metadata_gin' utilized in forced plan: {gin_used}")
        print(
            "Note: PostgreSQL optimizer legitimately selects Sequential Scan in Plan 1 because\n"
            "with a small table (e.g. 20 rows fitting in a single page), sequential page reads\n"
            "are faster than traversing GIN index pages plus heap table lookups."
        )
        print("=" * 70)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run EXPLAIN ANALYZE on JSONB metadata query")
    parser.add_argument("--field", default="category", help="Metadata field to filter on")
    parser.add_argument("--value", default="widget", help="Metadata value to match")
    args = parser.parse_args()

    try:
        await run_explain_analyze(filter_field=args.field, filter_value=args.value)
        return 0
    except Exception as exc:
        print(f"EXPLAIN ANALYZE failed: {exc}", file=sys.stderr)
        return 1
    finally:
        await dispose_engine()


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
