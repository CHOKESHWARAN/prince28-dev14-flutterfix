"""SQLAlchemy asynchronous database connection."""

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from flutterfix.config import get_settings


settings = get_settings()

# Read the database URL without exposing it in logs.
raw_url = settings.database_url.get_secret_value()

# Convert the URL into SQLAlchemy's URL format.
url = make_url(raw_url)

# Use asyncpg as the PostgreSQL driver.
if url.drivername == "postgresql":
    url = url.set(drivername="postgresql+asyncpg")

# asyncpg uses 'ssl', not 'sslmode'.
query = dict(url.query)
sslmode = query.pop("sslmode", None)

connect_args = {}

if sslmode in ("require", "verify-ca", "verify-full"):
    connect_args["ssl"] = True

# Remove sslmode from the URL before passing it to asyncpg.
url = url.set(query=query)

engine = create_async_engine(
    url,
    pool_pre_ping=True,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session