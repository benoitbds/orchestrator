"""Conversation memory management utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


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
