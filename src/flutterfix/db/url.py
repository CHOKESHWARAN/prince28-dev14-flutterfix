"""PostgreSQL URL parsing and asyncpg compatibility helpers."""

from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from sqlalchemy.engine import URL, make_url


def build_asyncpg_db_url(raw_url: str) -> tuple[URL, dict[str, Any]]:
    """Convert standard PostgreSQL connection strings to asyncpg-compatible URL and connect_args.

    Handles:
    - Driver name conversion to 'postgresql+asyncpg'
    - Neon SSL mapping (converts sslmode to connect_args['ssl'])
    - Stripping unsupported options such as channel_binding and sslmode from the URL query
    """
    # Clean query parameters that asyncpg doesn't accept
    parts = urlsplit(raw_url)
    query_params = parse_qs(parts.query)

    sslmode = query_params.pop("sslmode", [None])[0]
    query_params.pop("channel_binding", None)

    connect_args: dict[str, Any] = {}
    if (sslmode in ("require", "verify-ca", "verify-full")) or ("neon.tech" in parts.netloc):
        connect_args["ssl"] = True

    # Reconstruct query string without unsupported asyncpg parameters
    cleaned_query = urlencode(
        {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}, doseq=True
    )
    cleaned_raw_url = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, cleaned_query, parts.fragment)
    )

    url = make_url(cleaned_raw_url)
    if url.drivername in ("postgresql", "postgres"):
        url = url.set(drivername="postgresql+asyncpg")

    return url, connect_args
