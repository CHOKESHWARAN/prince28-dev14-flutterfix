from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request

from flutterfix.api.deps import RepoDep
from flutterfix.db.repository import ALLOWED_FILTER_KEYS, InvalidFilterError

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
async def list_documents(
    repo: RepoDep,
    request: Request,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    # Extract any extra query params as metadata filters
    excluded_params = {"q", "limit", "offset"}
    raw_filters = {
        key: val for key, val in request.query_params.items() if key not in excluded_params
    }

    # Validate filter keys
    for key in raw_filters:
        if key not in ALLOWED_FILTER_KEYS:
            allowed = sorted(ALLOWED_FILTER_KEYS)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid filter parameter '{key}'. Allowed: {allowed}",
            )

    try:
        items, total = await repo.list(q=q, limit=limit, offset=offset, filters=raw_filters)
    except InvalidFilterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get("/{doc_id}")
async def get_document(doc_id: str, repo: RepoDep) -> dict[str, Any]:
    record = await repo.get(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No document with id '{doc_id}'.")
    return record
