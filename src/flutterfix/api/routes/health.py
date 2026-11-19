<<<<<<< HEAD
from fastapi import APIRouter, Response

from flutterfix.api.deps import SettingsDep, StoreDep
=======
from typing import Any

from fastapi import APIRouter, Response
from sqlalchemy import text

from flutterfix.api.deps import SessionDep, SettingsDep
>>>>>>> backup/day-03-postgres

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    """Liveness: is the process alive? Instant. Never touches the DB or the LLM."""
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@router.get("/ready")
<<<<<<< HEAD
def ready(store: StoreDep, response: Response) -> dict:
    """Readiness: can this instance serve traffic right now?"""
    checks = {"records_loaded": store.ready}
    ok = all(checks.values())
    if not ok:
        response.status_code = 503
=======
async def ready(response: Response, session: SessionDep) -> dict[str, Any]:
    """Readiness: can this instance serve traffic right now? Verifies PostgreSQL connectivity."""
    db_ok = False
    try:
        result = await session.execute(text("SELECT 1"))
        db_ok = result.scalar_one() == 1
    except Exception:
        db_ok = False

    checks = {
        "database": db_ok,
        "records_loaded": db_ok,
    }
    ok = all(checks.values())
    if not ok:
        response.status_code = 503

>>>>>>> backup/day-03-postgres
    return {"status": "ready" if ok else "not_ready", "checks": checks}
