"""Service helpers for persisting agentic orchestration data."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Any, Mapping

from sqlmodel import Session

from .db import get_session
from .models import AgentSpan, BlobRef, Message, Run, ToolCall, ToolResult


def _ensure_run(run_id: str, session: Session) -> None:
    if session.get(Run, run_id) is None:
        raise ValueError("run not found")


def save_blob(kind: str, data: Any, *, session: Session | None = None) -> str:
    """Persist a blob and return its identifier."""
    payload = data if isinstance(data, str) else json.dumps(data, sort_keys=True)
    sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    blob = BlobRef(kind=kind, data=data, sha256=sha)
    if session is None:
        with get_session() as s:
            s.add(blob)
            s.commit()
            s.refresh(blob)
            return blob.id
    session.add(blob)
    session.commit()
    session.refresh(blob)
    return blob.id


def start_span(
    run_id: str,
    agent_name: str,
    *,
    input_ref: str | None = None,
    meta: dict | None = None,
    session: Session | None = None,
) -> str:
    if session is None:
        with get_session() as s:
            _ensure_run(run_id, s)
            span = AgentSpan(run_id=run_id, agent_name=agent_name, input_ref=input_ref, meta=meta)
            s.add(span)
            s.commit()
            s.refresh(span)
            return span.id
    _ensure_run(run_id, session)
    span = AgentSpan(run_id=run_id, agent_name=agent_name, input_ref=input_ref, meta=meta)
    session.add(span)
    session.commit()
    session.refresh(span)
    return span.id


def end_span(
    span_id: str,
    *,
    status: str = "ok",
    output_ref: str | None = None,
    meta: dict | None = None,
    session: Session | None = None,
) -> None:
    if session is None:
        with get_session() as s:
            span = s.get(AgentSpan, span_id)
            if span is None:
                raise ValueError("span not found")
            span.status = status
            span.output_ref = output_ref
            span.end_ts = datetime.utcnow()
            if meta:
                current = span.meta or {}
                current.update(meta)
                span.meta = current
            s.add(span)
            s.commit()
            return
    span = session.get(AgentSpan, span_id)
    if span is None:
        raise ValueError("span not found")
    span.status = status
    span.output_ref = output_ref
    span.end_ts = datetime.utcnow()
    if meta:
        current = span.meta or {}
        current.update(meta)
        span.meta = current
    session.add(span)
    session.commit()


def save_message(
    run_id: str,
    role: str,
    content: Any,
    *,
    agent_name: str | None = None,
    model: str | None = None,
    tokens: Mapping[str, int] | None = None,
    cost_eur: float | None = None,
    session: Session | None = None,
) -> str:
    if session is None:
        with get_session() as s:
            _ensure_run(run_id, s)
            content_ref = save_blob("message", content, session=s)
            msg = Message(
                run_id=run_id,
                agent_name=agent_name,
                role=role,
                content_ref=content_ref,
                model=model,
                cost_eur=cost_eur,
            )
            if tokens:
                msg.prompt_tokens = tokens.get("prompt")
                msg.completion_tokens = tokens.get("completion")
                msg.total_tokens = tokens.get("total")
            s.add(msg)
            s.commit()
            s.refresh(msg)
            return msg.id
    _ensure_run(run_id, session)
    content_ref = save_blob("message", content, session=session)
    msg = Message(
        run_id=run_id,
        agent_name=agent_name,
        role=role,
        content_ref=content_ref,
        model=model,
        cost_eur=cost_eur,
    )
    if tokens:
        msg.prompt_tokens = tokens.get("prompt")
        msg.completion_tokens = tokens.get("completion")
        msg.total_tokens = tokens.get("total")
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg.id


def save_tool_call(
    run_id: str,
    agent_name: str,
    tool_name: str,
    *,
    input_ref: str | None = None,
    span_id: str | None = None,
    session: Session | None = None,
) -> str:
    if session is None:
        with get_session() as s:
            _ensure_run(run_id, s)
            call = ToolCall(
                run_id=run_id,
                agent_name=agent_name,
                tool_name=tool_name,
                input_ref=input_ref,
                span_id=span_id,
            )
            s.add(call)
            s.commit()
            s.refresh(call)
            return call.id
    _ensure_run(run_id, session)
    call = ToolCall(
        run_id=run_id,
        agent_name=agent_name,
        tool_name=tool_name,
        input_ref=input_ref,
        span_id=span_id,
    )
    session.add(call)
    session.commit()
    session.refresh(call)
    return call.id


def save_tool_result(
    tool_call_id: str,
    status: str,
    *,
    output_ref: str | None = None,
    session: Session | None = None,
) -> str:
    if session is None:
        with get_session() as s:
            call = s.get(ToolCall, tool_call_id)
            if call is None:
                raise ValueError("tool call not found")
            result = ToolResult(
                run_id=call.run_id,
                tool_call_id=tool_call_id,
                status=status,
                output_ref=output_ref,
            )
            s.add(result)
            s.commit()
            s.refresh(result)
            return result.id
    call = session.get(ToolCall, tool_call_id)
    if call is None:
        raise ValueError("tool call not found")
    result = ToolResult(
        run_id=call.run_id,
        tool_call_id=tool_call_id,
        status=status,
        output_ref=output_ref,
    )
    session.add(result)
    session.commit()
    session.refresh(result)
    return result.id
