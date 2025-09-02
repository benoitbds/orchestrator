# orchestrator/settings.py
import os

LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_BACKOFF_CAP = float(os.getenv("LLM_BACKOFF_CAP", "8.0"))
LLM_PROVIDER_ORDER = [
    s.strip()
    for s in os.getenv("LLM_PROVIDER_ORDER", "openai,anthropic,mistral,local").split(
        ","
    )
]
LLM_RATE_PER_SEC = float(os.getenv("LLM_RATE_PER_SEC", "2.0"))
LLM_BUCKET_CAP = int(os.getenv("LLM_BUCKET_CAP", "5"))

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.1-mini")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")
