# orchestrator/llm/safe_invoke.py
import asyncio
import logging
from typing import Any, Sequence

from .errors import RateLimitedError, QuotaExceededError, ProviderExhaustedError
from .backoff import sleep_backoff, parse_retry_after
from .throttle import TokenBucket
from orchestrator.settings import (
    LLM_MAX_RETRIES,
    LLM_BACKOFF_CAP,
    LLM_RATE_PER_SEC,
    LLM_BUCKET_CAP,
)

log = logging.getLogger(__name__)
_bucket = TokenBucket(rate_per_sec=LLM_RATE_PER_SEC, capacity=LLM_BUCKET_CAP)


async def _invoke_threaded(llm, messages: Sequence[Any]):
    def _call():
        return llm.invoke(messages)

    try:
        return await asyncio.to_thread(_call)
    except Exception as e:
        # Try to detect OpenAI-style errors without hard dependency on their types.
        msg = str(e) or ""
        headers = getattr(e, "response_headers", {}) or getattr(e, "headers", {}) or {}
        status = getattr(e, "status_code", None) or getattr(
            getattr(e, "response", None), "status_code", None
        )

        # quota error
        if "insufficient_quota" in msg or "You exceeded your current quota" in msg:
            raise QuotaExceededError() from e

        # rate limit
        if status == 429 or "Too Many Requests" in msg:
            ra = parse_retry_after(headers)
            raise RateLimitedError(retry_after=ra, detail=msg) from e

        raise


async def try_invoke_single(llm, messages: Sequence[Any]):
    attempt = 0
    while True:
        attempt += 1
        if not _bucket.take():
            await sleep_backoff(1, base=0.2, cap=1.5)
        try:
            return await _invoke_threaded(llm, messages)
        except RateLimitedError as e:
            if attempt > LLM_MAX_RETRIES:
                raise
            if e.retry_after and e.retry_after > 0:
                await asyncio.sleep(e.retry_after)
            else:
                await sleep_backoff(attempt, cap=LLM_BACKOFF_CAP)
        except QuotaExceededError:
            raise


async def safe_invoke_with_fallback(providers, messages: Sequence[Any]):
    last_err = None
    for idx, llm in enumerate(providers):
        name = (
            getattr(llm, "name", None)
            or getattr(llm, "model_name", None)
            or f"provider_{idx}"
        )
        try:
            return await try_invoke_single(llm, messages)
        except QuotaExceededError as e:
            log.warning("Quota exceeded on %s, trying next provider…", name)
            last_err = e
            continue
        except RateLimitedError as e:
            log.warning(
                "Rate limit exhausted on %s after retries, trying next provider…", name
            )
            last_err = e
            continue
        except Exception as e:
            log.exception("Unexpected error on %s, trying next provider…", name)
            last_err = e
            continue
    raise ProviderExhaustedError() from last_err
