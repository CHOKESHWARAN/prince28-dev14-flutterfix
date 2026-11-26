from dataclasses import dataclass

from flutterfix.api.deps import get_gateway
from flutterfix.llm.gateway import LLMResult


@dataclass
class Result:
    text: str = "Flutter answer"
    provider: str = "gemini"
    model: str = "gemini-test"
    tokens_in: int = 5
    tokens_out: int = 3
    latency_ms: int = 12
    attempts: int = 1
    fallback_used: bool = False
    cost_inr: float = 0.001


class FakeGateway:
    async def generate(self, messages, **kwargs):
        return Result()

    async def stream(self, messages, **kwargs):
        yield "Flutter "
        yield "answer"
        yield LLMResult(
            text="Flutter answer",
            provider="gemini",
            model="gemini-test",
            tokens_in=5,
            tokens_out=3,
            latency_ms=12,
            attempts=1,
            fallback_used=False,
            cost_inr=0.001,
        )


class FakeUsage:
    async def by_day(self, days):
        return [
            {
                "day": "2026-11-25",
                "calls": 2,
                "errors": 0,
                "fallbacks": 0,
                "tokens_in": 10,
                "tokens_out": 6,
                "cost_inr": 0.002,
            }
        ]


def setup(client):
    client.app.dependency_overrides[get_gateway] = lambda: FakeGateway()

    async def usage():
        return FakeUsage()

    from flutterfix.api.deps import get_usage_repository

    client.app.dependency_overrides[get_usage_repository] = usage


def test_chat_json_response(client):
    setup(client)
    response = client.post("/v1/chat", json={"message": "Explain widgets", "stream": False})
    assert response.status_code == 200
    assert response.json()["answer"] == "Flutter answer"
    assert response.json()["provider"] == "gemini"


def test_chat_streams_sse_and_completion(client):
    setup(client)
    response = client.post("/v1/chat", json={"message": "Explain widgets"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"delta": "Flutter "' in response.text
    assert "event: done" in response.text


def test_usage_includes_daily_cost_summary(client):
    setup(client)
    response = client.get("/v1/usage")
    assert response.status_code == 200
    assert response.json()["calls"] == 2
    assert response.json()["total_cost_inr"] == 0.002


def test_chat_rejects_empty_message(client):
    response = client.post("/v1/chat", json={"message": ""})
    assert response.status_code == 422
