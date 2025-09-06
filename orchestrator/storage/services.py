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
    content: Any | None = None,
    *,
    content_ref: str | None = None,
    agent_name: str | None = None,
    model: str | None = None,
    tokens: Mapping[str, int] | None = None,
    cost_eur: float | None = None,
    ts: datetime | None = None,
    session: Session | None = None,
) -> str:
    """Persist a chat message.

    Either ``content`` or ``content_ref`` must be provided. If ``content`` is
    given, it will be stored as a blob and referenced automatically.
    """

    if content_ref is None:
        if content is None:
            raise ValueError("content or content_ref required")
    
    if session is None:
        with get_session() as s:
            _ensure_run(run_id, s)
            if content_ref is None:
                content_ref = save_blob("message", content, session=s)
            msg = Message(
                run_id=run_id,
                agent_name=agent_name,
                role=role,
                content_ref=content_ref,
                model=model,
                cost_eur=cost_eur,
                ts=ts or datetime.utcnow(),
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
    if content_ref is None:
        content_ref = save_blob("message", content, session=session)
    msg = Message(
        run_id=run_id,
        agent_name=agent_name,
        role=role,
        content_ref=content_ref,
        model=model,
        cost_eur=cost_eur,
        ts=ts or datetime.utcnow(),
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


def get_run_timeline(
    run_id: str, *, limit: int = 1000, session: Session | None = None
) -> list[dict]:
    """Return unified timeline events for a run from SQLModel storage."""
    if session is None:
        with get_session() as s:
            return _get_timeline_data(run_id, limit, s)
    return _get_timeline_data(run_id, limit, session)


def _get_timeline_data(run_id: str, limit: int, session: Session) -> list[dict]:
    """Internal helper to get timeline data."""
    from sqlmodel import select
    events: list[dict] = []
    
    # Get agent spans
    spans = session.exec(select(AgentSpan).where(AgentSpan.run_id == run_id)).all()
    for span in spans:
        # Agent span start event
        start_event = {
            "type": "agent.span.start",
            "ts": span.start_ts,
            "run_id": run_id,
            "agent": span.agent_name,
            "label": f"▶ {span.agent_name}",
            "ref": {"span_id": span.id},
            "meta": span.meta or {},
        }
        events.append(start_event)
        
        # Agent span end event (if completed)
        if span.end_ts:
            duration = (span.end_ts - span.start_ts).total_seconds()
            end_event = {
                "type": "agent.span.end",
                "ts": span.end_ts,
                "run_id": run_id,
                "agent": span.agent_name,
                "label": f"■ {span.agent_name} ({duration:.2f}s)",
                "ref": {"span_id": span.id},
                "meta": {"status": span.status or "ok", **(span.meta or {})},
            }
            events.append(end_event)
    
    # Get messages
    messages = session.exec(select(Message).where(Message.run_id == run_id)).all()
    for msg in messages:
        event = {
            "type": "message",
            "ts": msg.ts,
            "run_id": run_id,
            "agent": msg.agent_name,
            "label": f"{msg.role} message",
            "ref": {"message_id": msg.id},
            "meta": {
                "model": msg.model,
                "tokens": msg.total_tokens,
                "cost_eur": msg.cost_eur,
            },
        }
        events.append(event)
    
    # Get tool calls
    tool_calls = session.exec(select(ToolCall).where(ToolCall.run_id == run_id)).all()
    for call in tool_calls:
        event = {
            "type": "tool.call",
            "ts": call.ts,
            "run_id": run_id,
            "agent": call.agent_name,
            "label": f"call {call.tool_name}",
            "ref": {"tool_call_id": call.id},
            "meta": {},
        }
        events.append(event)
    
    # Get tool results
    tool_results = session.exec(select(ToolResult).where(ToolResult.run_id == run_id)).all()
    for result in tool_results:
        event = {
            "type": "tool.result",
            "ts": result.ts,
            "run_id": run_id,
            "agent": None,  # Will be derived from tool call
            "label": f"result",
            "ref": {"tool_result_id": result.id},
            "meta": {"status": result.status},
        }
        events.append(event)
    
    # Sort by timestamp and limit
    events.sort(key=lambda e: e["ts"])
    return events[:limit]


def get_run_cost(run_id: str, *, session: Session | None = None) -> dict:
    """Aggregate token and cost information for a run from SQLModel storage."""
    if session is None:
        with get_session() as s:
            return _get_cost_data(run_id, s)
    return _get_cost_data(run_id, session)


def _get_cost_data(run_id: str, session: Session) -> dict:
    """Internal helper to get cost data."""
    from sqlmodel import select, func
    
    # Get aggregated costs by agent
    query = select(
        Message.agent_name,
        func.coalesce(func.sum(Message.total_tokens), 0).label("tokens"),
        func.coalesce(func.sum(Message.cost_eur), 0.0).label("cost_eur"),
    ).where(Message.run_id == run_id).group_by(Message.agent_name)
    
    results = session.exec(query).all()
    
    by_agent = []
    total_tokens = 0
    total_cost = 0.0
    
    for agent_name, tokens, cost_eur in results:
        by_agent.append({
            "agent": agent_name,
            "tokens": int(tokens or 0),
            "cost_eur": float(cost_eur or 0.0),
        })
        total_tokens += int(tokens or 0)
        total_cost += float(cost_eur or 0.0)
    
    return {
        "by_agent": by_agent,
        "total": {
            "agent": None,
            "tokens": total_tokens,
            "cost_eur": total_cost,
        },
    }
