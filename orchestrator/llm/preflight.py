from __future__ import annotations

"""Preflight helpers for OpenAI chat messages.

``preflight_validate_messages`` ensures tool messages are only sent when the
immediately preceding assistant message contains a matching ``tool_calls``
entry. ``extract_tool_exchange_slice`` trims the history to the minimal slice
required for a trailing tool exchange.
"""

from typing import Dict, List, Optional
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
                logger.warning(
                    json.dumps(
                        {
                            "event": "drop_orphan_tool",
                            "tool_call_id": tool_id,
                            "reason": reason,
                            "idx": idx,
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


def extract_tool_exchange_slice(messages: List[Dict]) -> Optional[List[Dict]]:
    """Return minimal slice if *messages* ends with a tool exchange.

    The slice contains, in chronological order:

    * Last system message before the assistant (if any).
    * Last user/assistant message before the assistant (if any).
    * The assistant message with ``tool_calls``.
    * The trailing tool messages referencing that assistant.

    If the history does not end with tool messages, ``None`` is returned.
    """

    if not messages:
        return None

    i = len(messages) - 1
    tool_msgs: List[Dict] = []
    while i >= 0 and messages[i].get("role") == "tool":
        tool_msgs.insert(0, messages[i])
        i -= 1

    if not tool_msgs:
        return None

    # Find the assistant with tool_calls preceding the tool messages.
    j = i
    assistant_idx: Optional[int] = None
    while j >= 0:
        msg = messages[j]
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            assistant_idx = j
            break
        j -= 1

    if assistant_idx is None:
        return None

    # Last system and dialog messages before the assistant.
    idx_system: Optional[int] = None
    idx_dialog: Optional[int] = None
    for idx in range(assistant_idx - 1, -1, -1):
        role = messages[idx].get("role")
        if idx_system is None and role == "system":
            idx_system = idx
        if idx_dialog is None and role in ("user", "assistant"):
            idx_dialog = idx
        if idx_system is not None and idx_dialog is not None:
            break

    indices = [i for i in (idx_system, idx_dialog) if i is not None]
    indices.sort()

    slice_msgs = [messages[idx] for idx in indices]
    slice_msgs.append(messages[assistant_idx])
    slice_msgs.extend(tool_msgs)
    return slice_msgs


def chat_completions_create(client, messages: List[Dict], **kwargs):
    """Wrapper around ``client.chat.completions.create`` with message preflight."""
    clean = preflight_validate_messages(messages)
    return client.chat.completions.create(messages=clean, **kwargs)
