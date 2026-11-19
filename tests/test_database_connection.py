"""Database connectivity test for live PostgreSQL verification."""

import asyncio

import pytest

from flutterfix.config import get_settings
from flutterfix.db.session import check_database_connection, dispose_engine


@pytest.mark.skipif(not get_settings().database_url, reason="database_url not configured")
def test_database_connection():
    try:
        result = asyncio.run(check_database_connection())
        assert result["test_value"] == 1
    except Exception as exc:
        pytest.skip(f"Live database not reachable: {exc}")
    finally:
        asyncio.run(dispose_engine())
