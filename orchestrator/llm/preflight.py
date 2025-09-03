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


def _tc_to_lc_shape(tc: dict) -> dict | None:
    """Coerce tool call to LangChain shape."""
    if not isinstance(tc, dict):
        return None
    tcid = tc.get("id")
    name = tc.get("name")
    args = tc.get("args")
    if name and isinstance(args, dict):
        return {"id": tcid, "type": "tool_call", "name": name, "args": args}
    fn = tc.get("function") or {}
    name = name or fn.get("name")
    arguments = args if isinstance(args, dict) else fn.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except Exception:
            arguments = {}
    if isinstance(arguments, dict) and name:
        return {"id": tcid, "type": "tool_call", "name": name, "args": arguments}
    return None


def _normalize_assistant_with_tool_calls(raw_message: dict | Any) -> Dict[str, Any]:
    """Build assistant dict with LC-shaped tool_calls if any."""
    content = getattr(raw_message, "content", None)
    if isinstance(raw_message, dict):
        content = raw_message.get("content", content) or ""
    else:
        content = content or ""

    raw_tcs = []
    if isinstance(raw_message, dict):
        raw_tcs = raw_message.get("tool_calls") or []
    else:
        raw_tcs = getattr(raw_message, "tool_calls", None) or []

    tcs = []
    for tc in raw_tcs:
        coerced = _tc_to_lc_shape(tc or {})
        if coerced:
            tcs.append(coerced)

    out = {"role": "assistant", "content": content}
    if tcs:
        out["tool_calls"] = tcs
    return out


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
    role = _role_of(m)
    if role == "assistant":
        return _normalize_assistant_with_tool_calls(m)
    if role == "tool":
        return {
            "role": "tool",
            "content": _content_of(m),
            "tool_call_id": _tool_call_id_of(m),
        }
    if role == "system":
        return {"role": "system", "content": _content_of(m)}
    if role == "user":
        return {"role": "user", "content": _content_of(m)}
    return {"role": role or "user", "content": _content_of(m)}


def normalize_history(history: List[MessageLike]) -> List[Dict[str, Any]]:
    return [_to_openai_dict(m) for m in history]


def to_langchain_messages(msgs: List[Dict[str, Any]]) -> List[BaseMessage]:
    out: List[BaseMessage] = []
    for m in msgs:
        r = m.get("role")
        if r == "system":
            out.append(SystemMessage(content=m.get("content", "")))
        elif r == "user":
            out.append(HumanMessage(content=m.get("content", "")))
        elif r == "assistant":
            out.append(
                AIMessage(
                    content=m.get("content", ""),
                    tool_calls=m.get("tool_calls") or [],  # expects LC shape
                )
            )
        elif r == "tool":
            out.append(
                ToolMessage(
                    content=m.get("content", ""),
                    tool_call_id=m.get("tool_call_id") or "",
                )
            )
        else:
            out.append(HumanMessage(content=m.get("content", "")))
    return out


def preflight_validate_messages(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    last_ids: Optional[Set[str]] = None
    for i, m in enumerate(msgs):
        role = m.get("role")
        if role == "assistant":
            last_ids = _assistant_tool_ids(m)
            out.append(m)
        elif role == "tool":
            tcid = m.get("tool_call_id")
            if last_ids and tcid in last_ids:
                out.append(m)
            else:
                level = logging.WARNING if last_ids else logging.DEBUG
                logger.log(
                    level,
                    "drop_orphan_tool",
                    extra={"payload": {"tool_call_id": tcid, "idx": i}},
                )
        else:
            last_ids = None
            out.append(m)
    return out


def extract_tool_exchange_slice(
    msgs: List[MessageLike],
) -> Optional[List[Dict[str, Any]]]:
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


def to_langchain_messages(msgs: List[Dict[str, Any]]) -> List["BaseMessage"]:
    """Convert sanitized message dicts to LangChain BaseMessages."""
    result = []
    for msg in msgs:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "assistant":
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                result.append(AIMessage(content=content, tool_calls=tool_calls))
            else:
                result.append(AIMessage(content=content))
        elif role == "user":
            result.append(HumanMessage(content=content))
        elif role == "system":
            result.append(SystemMessage(content=content))
        elif role == "tool":
            tool_call_id = msg.get("tool_call_id", "")
            result.append(ToolMessage(content=content, tool_call_id=tool_call_id))
        else:
            result.append(ChatMessage(role=role, content=content))

    return result
