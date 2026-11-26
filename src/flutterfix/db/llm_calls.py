"""Persistence and daily rollups for LLM call records."""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flutterfix.db.models import LlmCall


class LlmCallRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(self, row: dict) -> None:
        self.session.add(LlmCall(**row))
        await self.session.commit()

    async def by_day(self, days: int = 7) -> list[dict]:
        cutoff = date.today() - timedelta(days=days - 1)
        stmt = (
            select(
                func.date(LlmCall.created_at).label("day"),
                func.count().label("calls"),
                func.count().filter(LlmCall.status == "error").label("errors"),
                func.count().filter(LlmCall.fallback_used.is_(True)).label("fallbacks"),
                func.coalesce(func.sum(LlmCall.tokens_in), 0).label("tokens_in"),
                func.coalesce(func.sum(LlmCall.tokens_out), 0).label("tokens_out"),
                func.coalesce(func.sum(LlmCall.cost_inr), 0).label("cost_inr"),
            )
            .where(func.date(LlmCall.created_at) >= cutoff)
            .group_by(func.date(LlmCall.created_at))
            .order_by(func.date(LlmCall.created_at))
        )
        result = await self.session.execute(stmt)
        return [
            {
                "day": str(r.day),
                "calls": r.calls,
                "errors": r.errors,
                "fallbacks": r.fallbacks,
                "tokens_in": r.tokens_in,
                "tokens_out": r.tokens_out,
                "cost_inr": float(r.cost_inr),
            }
            for r in result
        ]
