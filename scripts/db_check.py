"""Verify PostgreSQL / Neon connectivity and display database version."""

import asyncio
import sys

from flutterfix.db.session import check_database_connection, dispose_engine


async def main() -> int:
    try:
        info = await check_database_connection()
        print("Neon PostgreSQL connection: SUCCESS")
        print(f"Database test value: {info['test_value']}")
        print(f"PostgreSQL server version: {info['server_version']}")
        return 0
    except Exception as exc:
        print(f"Neon PostgreSQL connection FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        await dispose_engine()


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
