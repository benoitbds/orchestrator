from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Sequence, Set, Union

try:  # soft import
    from langchain_core.messages import (
        AIMessage,
        BaseMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )
except Exception:  # pragma: no cover - langchain not installed
    BaseMessage = object  # type: ignore
    AIMessage = HumanMessage = SystemMessage = ToolMessage = object  # type: ignore

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


def _normalize_ai_tool_calls(ai: AIMessage) -> AIMessage:
    """Ensure AIMessage.tool_calls follow LangChain's shape."""
    tcs: List[dict] = []
    seen: Set[str] = set()
    raw_tcs = getattr(ai, "tool_calls", None) or []
    extra_tcs = (getattr(ai, "additional_kwargs", {}) or {}).get("tool_calls") or []
    for tc in list(raw_tcs) + list(extra_tcs):
        coerced = _tc_to_lc_shape(tc or {})
        if coerced:
            key = json.dumps(coerced, sort_keys=True)
            if key not in seen:
                seen.add(key)
                tcs.append(coerced)

    return AIMessage(content=ai.content or "", tool_calls=tcs)


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


def build_payload_messages(
    msgs: Sequence[MessageLike],
) -> tuple[List[Dict[str, Any]], bool]:
    """Sanitize incoming messages and detect tool exchange slice."""
    history = list(msgs)
    slice_msgs = extract_tool_exchange_slice(history)
    if slice_msgs is not None:
        return slice_msgs, True
    sanitized = preflight_validate_messages(normalize_history(history))
    return sanitized, False


def to_langchain_messages(
    msgs: Sequence[Union[Dict[str, Any], BaseMessage]]
) -> List[BaseMessage]:
    """Accept sanitized dicts or BaseMessages and return LangChain messages."""
    out: List[BaseMessage] = []
    for msg in msgs:
        if isinstance(msg, BaseMessage):
            if isinstance(msg, AIMessage):
                out.append(_normalize_ai_tool_calls(msg))
            else:
                out.append(msg)
            continue

        role = msg.get("role", "")
        content = msg.get("content", "") or ""
        if role == "system":
            out.append(SystemMessage(content=content))
        elif role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            tcs = []
            for tc in msg.get("tool_calls") or []:
                coerced = _tc_to_lc_shape(tc or {})
                if coerced:
                    tcs.append(coerced)
            out.append(AIMessage(content=content, tool_calls=tcs))
        elif role == "tool":
            out.append(
                ToolMessage(content=content, tool_call_id=msg.get("tool_call_id") or "")
            )
        else:
            out.append(HumanMessage(content=content))
    return out


