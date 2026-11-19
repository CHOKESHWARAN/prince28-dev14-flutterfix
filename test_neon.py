
import asyncio

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from flutterfix.config import get_settings


async def main():
    raw_url = get_settings().database_url.get_secret_value()

    url = make_url(raw_url)

    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+asyncpg")

    # asyncpg uses ssl rather than sslmode.
    query = dict(url.query)
    sslmode = query.pop("sslmode", None)

    connect_args = {}
    if sslmode in ("require", "verify-ca", "verify-full"):
        connect_args["ssl"] = True

    url = url.set(query=query)

    engine = create_async_engine(
        url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )

    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            print("Neon PostgreSQL connection: SUCCESS")
            print("Database test:", result.scalar_one())
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
