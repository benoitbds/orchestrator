# orchestrator/llm/factory.py
import os
from typing import Any


def build_llm(provider: str, *, temperature: float = 0.2) -> Any | None:
    p = provider.lower().strip()
    if p == "openai" and os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-5.1-mini"), temperature=temperature
        )
    if p == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest"),
            temperature=temperature,
        )
    if p == "mistral" and os.getenv("MISTRAL_API_KEY"):
        from langchain_mistralai import ChatMistralAI

        return ChatMistralAI(
            model=os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
            temperature=temperature,
        )
    if p == "local":
        # Optional local adapter; return None if not configured.
        try:
            from .local_adapter import LocalChatModel  # if you have one

            return LocalChatModel()
        except Exception:
            return None
    return None
