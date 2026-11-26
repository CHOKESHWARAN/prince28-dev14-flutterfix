"""Direct, minimal smoke tests for configured OpenAI-compatible providers."""

import asyncio
import time

import httpx

from flutterfix.config import get_settings


async def ping(client, name, base, key, model):
    if not key:
        print(f"{name} FAILED no API key configured")
        return
    start = time.perf_counter()
    try:
        response = await client.post(
            base.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Reply with pong"}],
                "max_tokens": 10,
            },
        )
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage", {})
        text = data["choices"][0]["message"]["content"]
        latency = int((time.perf_counter() - start) * 1000)
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        print(
            f"{name} OK {model} said {text!r} in {latency} ms, "
            f"tokens in={tokens_in} out={tokens_out}"
        )
    except Exception as exc:
        print(f"{name} FAILED {type(exc).__name__}: {exc}")


async def main():
    s = get_settings()
    async with httpx.AsyncClient(timeout=s.llm_timeout_seconds) as client:
        await ping(client, "gemini", s.llm_primary_base_url, s.gemini_api_key, s.llm_primary_model)
        await ping(client, "groq", s.llm_fallback_base_url, s.groq_api_key, s.llm_fallback_model)


if __name__ == "__main__":
    asyncio.run(main())
