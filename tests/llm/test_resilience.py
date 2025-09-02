# tests/llm/test_resilience.py
import pytest

from orchestrator.llm.safe_invoke import safe_invoke_with_fallback, try_invoke_single
from orchestrator.llm.errors import ProviderExhaustedError
from orchestrator.llm.throttle import TokenBucket


class DummyLLM:
    def __init__(self, behavior: str, succeed_on_attempt: int | None = None):
        self.behavior = behavior
        self.counter = 0
        self.succeed_on_attempt = succeed_on_attempt

    def invoke(self, messages):
        self.counter += 1
        if self.behavior == "quota":
            raise Exception("You exceeded your current quota (insufficient_quota)")
        if self.behavior == "ratelimit":
            if self.succeed_on_attempt and self.counter >= self.succeed_on_attempt:
                return {"ok": True, "provider": "ratelimit_dummy"}
            e = Exception("HTTP/1.1 429 Too Many Requests")
            setattr(e, "status_code", 429)
            setattr(e, "response_headers", {"retry-after": "0.1"})
            raise e
        if self.behavior == "ok":
            return {"ok": True, "provider": "ok_dummy"}
        if self.behavior == "error":
            raise Exception("some other error")
        return {"ok": True}


@pytest.mark.asyncio
async def test_quota_fallback():
    a = DummyLLM("quota")
    b = DummyLLM("ok")
    out = await safe_invoke_with_fallback([a, b], [{"role": "user", "content": "hi"}])
    assert out["ok"] is True
    assert out["provider"] == "ok_dummy"


@pytest.mark.asyncio
async def test_rate_limit_then_success():
    a = DummyLLM("ratelimit", succeed_on_attempt=3)
    out = await try_invoke_single(a, [{"role": "user", "content": "hi"}])
    assert out["ok"] is True
    assert a.counter >= 3


@pytest.mark.asyncio
async def test_all_providers_exhausted():
    a = DummyLLM("quota")
    b = DummyLLM("ratelimit", succeed_on_attempt=None)  # always 429
    with pytest.raises(ProviderExhaustedError):
        await safe_invoke_with_fallback([a, b], [{"role": "user", "content": "hi"}])


def test_token_bucket():
    bucket = TokenBucket(rate_per_sec=2.0, capacity=2)
    assert bucket.take() is True
    assert bucket.take() is True
    # third immediate take should fail until refill
    assert bucket.take() is False
