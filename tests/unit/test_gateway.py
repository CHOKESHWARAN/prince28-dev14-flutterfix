import pytest

from flutterfix.llm.gateway import (
    FakeLLM,
    LLMError,
    LLMGateway,
    LLMUnavailable,
    cost_inr,
)


@pytest.mark.asyncio
async def test_generate_records_cost_and_provider():
    rows = []

    async def recorder(row):
        rows.append(row)

    provider = FakeLLM(name="gemini", model="gemini-3.8-flash", script=["hello world"])
    gateway = LLMGateway([provider], recorder=recorder)
    result = await gateway.generate([{"role": "user", "content": "hi"}])
    assert result.text == "hello world"
    assert result.tokens_in == 12
    assert rows[0]["status"] == "ok"
    assert rows[0]["provider"] == "gemini"


@pytest.mark.asyncio
async def test_falls_back_after_provider_error():
    failed = FakeLLM(name="gemini", script=[LLMError("offline", retryable=False)])
    backup = FakeLLM(name="groq", script=["backup answer"])
    result = await LLMGateway([failed, backup]).generate([])
    assert result.provider == "groq"
    assert result.fallback_used is True


@pytest.mark.asyncio
async def test_stream_does_not_switch_after_partial_output():
    failed = FakeLLM(script=[("ignored", LLMError("stream broke", retryable=False))])
    backup = FakeLLM(name="groq")
    stream = LLMGateway([failed, backup]).stream([])
    assert await anext(stream) == "Half "
    with pytest.raises(LLMUnavailable):
        async for _ in stream:
            pass
    assert backup.calls == 0


def test_price_is_calculated_in_rupees():
    assert cost_inr("openai/gpt-oss-20b", 1_000_000, 0, 95) == 7.125
