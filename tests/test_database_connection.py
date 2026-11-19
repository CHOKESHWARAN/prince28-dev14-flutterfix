
import asyncio

from sqlalchemy import text

from flutterfix.database import engine


async def check_database():
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        return result.scalar_one()


def test_database_connection():
    result = asyncio.run(check_database())
    assert result == 1
