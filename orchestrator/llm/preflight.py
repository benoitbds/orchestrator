from __future__ import annotations

"""Preflight validation for OpenAI chat messages.

Ensures tool messages are only sent when the immediately preceding assistant
message contains a matching tool_calls entry.
"""

from typing import List, Dict
import logging
import json

logger = logging.getLogger(__name__)


def preflight_validate_messages(messages: List[Dict]) -> List[Dict]:
    """Return a sanitized copy of *messages* with invalid tool messages dropped.

    A tool message is kept only if:
    * The immediately preceding message is an assistant message with a
      ``tool_calls`` entry whose ``id`` matches the tool message's
      ``tool_call_id``.
    * No other messages appear between the assistant and tool message.

    Offending tool messages are removed and a structured warning is logged.
    The original list is not mutated.
    """

    sanitized: List[Dict] = []
    last_tool_ids: set[str] = set()
    expecting_tool = False  # True if last kept message was assistant w/ tool calls

    for idx, msg in enumerate(messages):
        role = msg.get("role")
        if role == "assistant":
            sanitized.append(msg.copy())
            tool_calls = msg.get("tool_calls") or []
            last_tool_ids = {
                tc.get("id")
                for tc in tool_calls
                if isinstance(tc, dict) and tc.get("id")
            }
            expecting_tool = bool(last_tool_ids)
        elif role == "tool":
            tool_id = msg.get("tool_call_id")
            if expecting_tool and tool_id in last_tool_ids:
                sanitized.append(msg.copy())
            else:
                reason = (
                    "missing parent assistant"
                    if not expecting_tool
                    else "unknown tool_call_id"
                )
                excerpt = [
                    {"index": i, "role": messages[i].get("role")}
                    for i in range(max(0, idx - 2), min(len(messages), idx + 3))
                ]
                logger.warning(
                    json.dumps(
                        {
                            "tool_call_id": tool_id,
                            "reason": reason,
                            "excerpt": excerpt,
                        }
                    )
                )
            # Whether kept or dropped, allow further tool messages for the same
            # assistant so long as there are declared tool IDs.
            expecting_tool = bool(last_tool_ids)
        else:
            sanitized.append(msg.copy())
            expecting_tool = False

    return sanitized


def chat_completions_create(client, messages: List[Dict], **kwargs):
    """Wrapper around ``client.chat.completions.create`` with message preflight."""
    clean = preflight_validate_messages(messages)
    return client.chat.completions.create(messages=clean, **kwargs)
