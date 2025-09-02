# orchestrator/llm/errors.py
class RateLimitedError(Exception):
    def __init__(self, retry_after: float | None = None, detail: str | None = None):
        super().__init__(detail)
        self.retry_after = retry_after


class QuotaExceededError(Exception):
    pass


class ProviderExhaustedError(Exception):
    pass
