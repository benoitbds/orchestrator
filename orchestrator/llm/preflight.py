from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Set, Union

try:  # soft import
    from langchain_core.messages import (
        AIMessage,
        BaseMessage,
        ChatMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )
except Exception:  # pragma: no cover - langchain not installed
    BaseMessage = object  # type: ignore
    AIMessage = HumanMessage = SystemMessage = ToolMessage = ChatMessage = object  # type: ignore

logger = logging.getLogger(__name__)

MessageLike = Union[Dict[str, Any], "BaseMessage"]


def _role_of(m: MessageLike) -> str:
    if isinstance(m, dict):
        return m.get("role") or ""
    t = getattr(m, "type", None)
    if t == "human":
        return "user"
    if t == "ai":
        return "assistant"
    if t == "system":
        return "system"
    if t == "tool":
        return "tool"
    return getattr(m, "role", "") or ""


def _assistant_tool_ids(m: MessageLike) -> Set[str]:
    ids: Set[str] = set()
    if isinstance(m, dict):
        for tc in m.get("tool_calls") or []:
            tcid = (tc or {}).get("id")
            if isinstance(tcid, str):
                ids.add(tcid)
        return ids
    if isinstance(m, AIMessage):
        for tc in getattr(m, "tool_calls", None) or []:
            tcid = (tc or {}).get("id")
            if isinstance(tcid, str):
                ids.add(tcid)
    return ids


def _tool_call_id_of(m: MessageLike) -> Optional[str]:
    if isinstance(m, dict):
        tcid = m.get("tool_call_id")
        return tcid if isinstance(tcid, str) else None
    if isinstance(m, ToolMessage):
        return getattr(m, "tool_call_id", None)
    return None


def _content_of(m: MessageLike) -> str:
    if isinstance(m, dict):
        c = m.get("content")
        return c if isinstance(c, str) else ""
    return getattr(m, "content", "") or ""


def _to_openai_dict(m: MessageLike) -> Dict[str, Any]:
    if isinstance(m, dict):
        return dict(m)

    role = _role_of(m)
    if role == "user":
        return {"role": "user", "content": _content_of(m)}
    if role == "system":
        return {"role": "system", "content": _content_of(m)}
    if role == "assistant":
        tcs = []
        if isinstance(m, AIMessage):
            for tc in getattr(m, "tool_calls", None) or []:
                fn = (tc or {}).get("function") or {}
                args = fn.get("arguments")
                if not isinstance(args, str):
                    try:
                        args = json.dumps(args)
                    except Exception:
                        args = str(args)
                tcs.append(
                    {
                        "id": tc.get("id"),
                        "type": tc.get("type") or "function",
                        "function": {
                            "name": fn.get("name") or "",
                            "arguments": args or "{}",
                        },
                    }
                )
        data: Dict[str, Any] = {"role": "assistant", "content": _content_of(m)}
        if tcs:
            data["tool_calls"] = tcs
        return data
    if role == "tool":
        return {
            "role": "tool",
            "content": _content_of(m),
            "tool_call_id": _tool_call_id_of(m),
        }
    return {"role": role or "user", "content": _content_of(m)}


def normalize_history(history: List[MessageLike]) -> List[Dict[str, Any]]:
    return [_to_openai_dict(m) for m in history]


def preflight_validate_messages(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    last_assistant_tool_ids: Optional[Set[str]] = None
    for i, m in enumerate(msgs):
        role = m.get("role")
        if role == "assistant":
            last_assistant_tool_ids = _assistant_tool_ids(m)
            out.append(m)
        elif role == "tool":
            tcid = m.get("tool_call_id")
            if last_assistant_tool_ids and tcid in last_assistant_tool_ids:
                out.append(m)
            else:
                logger.warning(
                    "drop_orphan_tool",
                    extra={
                        "payload": {
                            "tool_call_id": tcid,
                            "idx": i,
                            "reason": "no_adjacent_parent",
                        }
                    },
                )
        else:
            last_assistant_tool_ids = None
            out.append(m)
    return out


def extract_tool_exchange_slice(msgs: List[MessageLike]) -> Optional[List[Dict[str, Any]]]:
    n = len(msgs)
    if n == 0:
        return None
    nd = normalize_history(msgs)
    i = n - 1
    tools_tail: List[Dict[str, Any]] = []
    while i >= 0 and nd[i].get("role") == "tool":
        tools_tail.append(nd[i])
        i -= 1
    if i >= 0 and nd[i].get("role") == "assistant" and _assistant_tool_ids(nd[i]):
        tail = [nd[i]] + list(reversed(tools_tail))
        head: List[Dict[str, Any]] = []
        for j in range(i - 1, -1, -1):
            if nd[j].get("role") == "system":
                head = [nd[j]]
                break
        if i - 1 >= 0 and nd[i - 1].get("role") in ("user", "assistant"):
            head.append(nd[i - 1])
        slice_msgs = head + tail
        validated = preflight_validate_messages(slice_msgs)
        if not validated or validated[-1].get("role") != "tool":
            return None
        return validated
    return None

