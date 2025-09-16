"""Conversation memory management utilities."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Sequence

import openai


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatMessage:
    """Container for an individual chat message."""

    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        """Convert the message to a serialisable dictionary."""
        return {"role": self.role, "content": self.content}


class ConversationMemory:
    """Manage chat history and an optional summary for a conversation."""

    SUMMARIZE_THRESHOLD = 10
    SUMMARY_RECENT_MESSAGES = 5
    SUMMARY_MODEL = "gpt-3.5-turbo"

    def __init__(self) -> None:
        self._messages: List[ChatMessage] = []
        self.summary: str = ""

    def add_message(self, role: str, content: str) -> None:
        """Add a validated chat message to the conversation history."""
        if not isinstance(role, str) or not role.strip():
            raise ValueError("role must be a non-empty string")
        if not isinstance(content, str):
            raise ValueError("content must be a string")

        self._messages.append(ChatMessage(role=role.strip(), content=content))
        self._maybe_summarize()

    def update_summary(self, summary: str) -> None:
        """Replace the stored conversation summary."""
        if not isinstance(summary, str):
            raise ValueError("summary must be a string")
        self.summary = summary.strip()

    def get_recent_messages(self, n: int = 5) -> List[dict[str, str]]:
        """Return the latest messages, optionally prefixed with the summary."""
        if not isinstance(n, int) or n <= 0:
            raise ValueError("n must be a positive integer")

        recent: Sequence[ChatMessage] = self._messages[-n:]
        recent_as_dicts = [message.to_dict() for message in recent]

        if self.summary:
            summary_message = {
                "role": "system",
                "content": f"Summary of previous conversation: {self.summary}",
            }
            return [summary_message, *recent_as_dicts]

        return recent_as_dicts.copy()

    @property
    def messages(self) -> List[dict[str, str]]:
        """Expose a copy of the entire message history."""
        return [message.to_dict() for message in self._messages]

    def summarize_conversation(self) -> bool:
        """Summarize older conversation history via the OpenAI API.

        Returns ``True`` when a summary was generated and history trimmed, ``False``
        when no summarisation was required (e.g. below threshold).
        """

        if len(self._messages) <= self.SUMMARIZE_THRESHOLD:
            return False

        keep = min(len(self._messages), self.SUMMARY_RECENT_MESSAGES)
        cutoff = len(self._messages) - keep
        if cutoff <= 0:
            return False

        old_messages = self._messages[:cutoff]
        if not old_messages:
            return False

        conversation_text = "\n".join(
            f"{message.role}: {message.content}" for message in old_messages
        )

        existing_summary = self.summary or "None"
        prompt = (
            "You maintain a concise running summary of a chat conversation.\n"
            "Update the summary using the additional messages while keeping key"
            " decisions and next steps."
        )
        user_content = (
            f"Existing summary:\n{existing_summary}\n\n"
            f"Additional conversation:\n{conversation_text}\n\n"
            "Respond with the updated summary only."
        )

        try:
            response = openai.ChatCompletion.create(
                model=self.SUMMARY_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": prompt,
                    },
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
                max_tokens=256,
            )
        except Exception as exc:  # pragma: no cover - specific exceptions depend on SDK
            raise RuntimeError("OpenAI conversation summarization failed") from exc

        try:
            summary_text = (
                response["choices"][0]["message"]["content"].strip()
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "OpenAI conversation summarization returned an unexpected payload"
            ) from exc

        if not summary_text:
            raise RuntimeError(
                "OpenAI conversation summarization returned an empty summary"
            )

        self.update_summary(summary_text)
        self._messages = list(self._messages[cutoff:])

        return True

    def _maybe_summarize(self) -> None:
        try:
            self.summarize_conversation()
        except RuntimeError as exc:
            logger.warning("Skipping conversation summarization: %s", exc)
