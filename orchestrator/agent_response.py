"""Response generation leveraging conversation memory and external search."""
from __future__ import annotations

import logging
from typing import Final

import openai

from orchestrator.conversation_memory import ConversationMemory
from orchestrator.external_info import retrieve_external_info

logger = logging.getLogger(__name__)

DEFAULT_CHAT_MODEL: Final[str] = "gpt-3.5-turbo"
RECENT_MESSAGE_COUNT: Final[int] = 5
FALLBACK_ASSISTANT_RESPONSE: Final[str] = (
    "*(Error: I couldn't generate a response at this time.)*"
)


def _prune_duplicate_user_message(
    history: list[dict[str, str]], user_input: str
) -> list[dict[str, str]]:
    """Return *history* without a trailing duplicate of *user_input*."""

    if history and history[-1].get("role") == "user" and history[-1].get("content") == user_input:
        return history[:-1]

    return list(history)


def generate_agent_response(
    user_input: str,
    memory: ConversationMemory,
    *,
    system_prompt: str,
    model: str = DEFAULT_CHAT_MODEL,
    recent_message_count: int = RECENT_MESSAGE_COUNT,
) -> str:
    """Generate an assistant reply using conversation memory and external info."""

    if not isinstance(memory, ConversationMemory):
        raise TypeError("memory must be an instance of ConversationMemory")

    if not isinstance(user_input, str) or not user_input.strip():
        raise ValueError("user_input must be a non-empty string")

    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ValueError("system_prompt must be a non-empty string")

    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string")

    if not isinstance(recent_message_count, int) or recent_message_count <= 0:
        raise ValueError("recent_message_count must be a positive integer")

    memory.add_message("user", user_input)

    try:
        memory.summarize_conversation()
    except RuntimeError as exc:  # pragma: no cover - exercised via logging
        logger.warning(
            "Skipping conversation summarization during response generation: %s",
            exc,
        )

    try:
        external_info = retrieve_external_info(user_input)
    except Exception as exc:  # pragma: no cover - depends on HTTP failure types
        logger.warning("Failed to retrieve external information: %s", exc)
        external_info = ""

    messages = [{"role": "system", "content": system_prompt.strip()}]

    if external_info:
        messages.append(
            {"role": "system", "content": f"Relevant information: {external_info}"}
        )

    recent_history = memory.get_recent_messages(n=recent_message_count)
    messages.extend(_prune_duplicate_user_message(recent_history, user_input))
    messages.append({"role": "user", "content": user_input})

    try:
        response = openai.ChatCompletion.create(model=model, messages=messages)
        assistant_reply = response["choices"][0]["message"]["content"].strip()
        if not assistant_reply:
            raise KeyError("empty response")
    except Exception as exc:  # pragma: no cover - SDK/network dependent
        logger.warning("OpenAI ChatCompletion failed: %s", exc)
        assistant_reply = FALLBACK_ASSISTANT_RESPONSE

    memory.add_message("assistant", assistant_reply)

    return assistant_reply
