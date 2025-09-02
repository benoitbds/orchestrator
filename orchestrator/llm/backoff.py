# orchestrator/llm/backoff.py
import asyncio
import random


async def sleep_backoff(attempt: int, base: float = 0.5, cap: float = 8.0):
    delay = min(cap, base * (2 ** (attempt - 1))) + random.random() * 0.2
    await asyncio.sleep(delay)


def parse_retry_after(headers: dict) -> float | None:
    if not headers:
        return None
    for k in (
        "retry-after",
        "Retry-After",
        "x-ratelimit-reset-requests",
        "x-ratelimit-reset-tokens",
    ):
        v = headers.get(k)
        if v is None:
            continue
        try:
            return float(v)
        except Exception:
            pass
    return None
