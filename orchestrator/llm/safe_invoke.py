# orchestrator/llm/safe_invoke.py
import asyncio
import logging
from typing import Any, Sequence

from .errors import RateLimitedError, QuotaExceededError, ProviderExhaustedError
from .backoff import sleep_backoff, parse_retry_after
from .throttle import TokenBucket
from .preflight import preflight_validate_messages, extract_tool_exchange_slice
from orchestrator.settings import (
    LLM_MAX_RETRIES,
    LLM_BACKOFF_CAP,
    LLM_RATE_PER_SEC,
    LLM_BUCKET_CAP,
)

log = logging.getLogger(__name__)
_bucket = TokenBucket(rate_per_sec=LLM_RATE_PER_SEC, capacity=LLM_BUCKET_CAP)
in_tool_exchange = False
TOOL_EXCHANGE_MODEL = "gpt-4o-mini"


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


async def try_invoke_single(llm, messages: Sequence[Any], model_override: str | None = None):
    attempt = 0
    while True:
        attempt += 1
        if not _bucket.take():
            await sleep_backoff(1, base=0.2, cap=1.5)
        orig_model = orig_model_name = None
        try:
            if model_override:
                if hasattr(llm, "model"):
                    orig_model = getattr(llm, "model")
                    llm.model = model_override
                if hasattr(llm, "model_name"):
                    orig_model_name = getattr(llm, "model_name")
                    llm.model_name = model_override
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
        finally:
            if model_override:
                if orig_model is not None:
                    llm.model = orig_model
                if orig_model_name is not None:
                    llm.model_name = orig_model_name


async def safe_invoke_with_fallback(providers, messages: Sequence[Any]):
    global in_tool_exchange
    last_err = None

    history = list(messages)
    slice_msgs = extract_tool_exchange_slice(history)
    to_send = preflight_validate_messages(slice_msgs or history)

    for idx, llm in enumerate(providers):
        name = (
            getattr(llm, "name", None)
            or getattr(llm, "model_name", None)
            or f"provider_{idx}"
        )
        try:
            rsp = await try_invoke_single(
                llm,
                to_send,
                model_override=TOOL_EXCHANGE_MODEL if in_tool_exchange else None,
            )
        except QuotaExceededError as e:
            if in_tool_exchange:
                log.warning("Quota exceeded on %s during tool exchange; skipping fallback", name)
                raise
            log.warning("Quota exceeded on %s, trying next provider…", name)
            last_err = e
            continue
        except RateLimitedError as e:
            if in_tool_exchange:
                log.warning("Rate limit exhausted on %s during tool exchange; skipping fallback", name)
                raise
            log.warning(
                "Rate limit exhausted on %s after retries, trying next provider…", name
            )
            last_err = e
            continue
        except Exception as e:
            if in_tool_exchange:
                log.exception("Unexpected error on %s during tool exchange; skipping fallback", name)
                raise
            log.exception("Unexpected error on %s, trying next provider…", name)
            last_err = e
            continue

        tcs = getattr(rsp, "tool_calls", None) or []
        if tcs and not in_tool_exchange:
            log.info("Entering tool exchange")
            in_tool_exchange = True
        elif in_tool_exchange and not tcs:
            log.info("Exiting tool exchange")
            in_tool_exchange = False
        return rsp
    raise ProviderExhaustedError() from last_err
