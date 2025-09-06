"""Structured event system for orchestration runs."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque

from orchestrator.crud import get_conn
import uuid
import json


# Event buffer: run_id -> deque of events (keep last N events in memory)
_event_buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
_seq_counters: Dict[str, int] = defaultdict(int)
_run_start_times: Dict[str, datetime] = {}

# Stream queues for WebSocket (existing stream.py functionality)
_streams: Dict[str, asyncio.Queue] = {}


def start_run(run_id: str) -> None:
    """Mark the start time for a run."""
    _run_start_times[run_id] = datetime.utcnow()
    _seq_counters[run_id] = 0


def emit_event(
    run_id: str,
    event_type: str,
    data: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    tokens: Optional[Dict[str, int]] = None,
    cost_eur: Optional[float] = None,
    tool_call_id: Optional[str] = None,
) -> int:
    """Emit a structured event for a run."""
    seq = _seq_counters[run_id]
    _seq_counters[run_id] += 1
    
    now = datetime.utcnow()
    start_time = _run_start_times.get(run_id, now)
    elapsed_ms = int((now - start_time).total_seconds() * 1000)
    
    # Create the event
    event = {
        "run_id": run_id,
        "seq": seq,
        "event_type": event_type,
        "ts": now.isoformat(),
        "elapsed_ms": elapsed_ms,
        "model": model,
        "prompt_tokens": tokens.get("prompt") if tokens else None,
        "completion_tokens": tokens.get("completion") if tokens else None,
        "total_tokens": tokens.get("total") if tokens else None,
        "cost_eur": cost_eur,
        "tool_call_id": tool_call_id,
        "data": data,
    }
    
    # Buffer the event in memory
    _event_buffers[run_id].append(event)
    
    # Persist to database
    conn = get_conn()
    conn.execute(
        "INSERT INTO run_events (id, run_id, seq, event_type, ts, elapsed_ms, model, prompt_tokens, completion_tokens, total_tokens, cost_eur, tool_call_id, data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            run_id,
            seq,
            event_type,
            now.isoformat(),
            elapsed_ms,
            model,
            tokens.get("prompt") if tokens else None,
            tokens.get("completion") if tokens else None,
            tokens.get("total") if tokens else None,
            cost_eur,
            tool_call_id,
            json.dumps(data) if data else None,
        ),
    )
    conn.commit()
    conn.close()
    
    # Stream to WebSocket clients (compatible with existing stream.py)
    if run_id in _streams:
        stream_event = {
            "event_type": event_type,
            "seq": seq,
            "ts": now.isoformat(),
            "elapsed_ms": elapsed_ms,
            "data": data,
        }
        if model:
            stream_event["model"] = model
        if tokens:
            stream_event["tokens"] = tokens
        if cost_eur:
            stream_event["cost_eur"] = cost_eur
        if tool_call_id:
            stream_event["tool_call_id"] = tool_call_id
            
        try:
            _streams[run_id].put_nowait(stream_event)
        except asyncio.QueueFull:
            pass  # Drop events if queue is full
    
    return seq


def get_events(run_id: str, since: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get buffered events for a run, optionally since a sequence number."""
    events = list(_event_buffers[run_id])
    if since is not None:
        events = [e for e in events if e["seq"] > since]
    return events


def get_events_from_db(run_id: str, since: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get events from database (fallback for older events not in buffer)."""
    conn = get_conn()
    
    if since is not None:
        rows = conn.execute(
            "SELECT run_id, seq, event_type, ts, elapsed_ms, model, prompt_tokens, completion_tokens, total_tokens, cost_eur, tool_call_id, data FROM run_events WHERE run_id=? AND seq > ? ORDER BY seq",
            (run_id, since),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT run_id, seq, event_type, ts, elapsed_ms, model, prompt_tokens, completion_tokens, total_tokens, cost_eur, tool_call_id, data FROM run_events WHERE run_id=? ORDER BY seq",
            (run_id,),
        ).fetchall()
    
    conn.close()
    
    events = []
    for row in rows:
        event = {
            "run_id": row[0],
            "seq": row[1],
            "event_type": row[2],
            "ts": row[3],
            "elapsed_ms": row[4],
            "model": row[5],
            "prompt_tokens": row[6],
            "completion_tokens": row[7],
            "total_tokens": row[8],
            "cost_eur": row[9],
            "tool_call_id": row[10],
            "data": json.loads(row[11]) if row[11] else None,
        }
        events.append(event)
    
    return events


def register_stream(run_id: str) -> asyncio.Queue:
    """Register a WebSocket stream for events."""
    queue = asyncio.Queue(maxsize=50)
    _streams[run_id] = queue
    return queue


def unregister_stream(run_id: str) -> None:
    """Unregister a WebSocket stream."""
    if run_id in _streams:
        try:
            _streams[run_id].put_nowait(None)  # Signal end
        except asyncio.QueueFull:
            pass
        del _streams[run_id]


def cleanup_run(run_id: str) -> None:
    """Clean up memory structures for a completed run."""
    _event_buffers.pop(run_id, None)
    _seq_counters.pop(run_id, None)
    _run_start_times.pop(run_id, None)
    unregister_stream(run_id)


# Event type constants
class EventType:
    PLAN = "plan"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ASSISTANT_ANSWER = "assistant_answer"
    STATUS_UPDATE = "status_update"
    ERROR = "error"


# Convenience functions for common event types
def emit_plan(run_id: str, plan_text: str, model: str = None, tokens: dict = None) -> int:
    """Emit a plan event."""
    return emit_event(run_id, EventType.PLAN, {"plan": plan_text}, model=model, tokens=tokens)


def emit_tool_call(
    run_id: str, 
    tool_name: str, 
    args: dict, 
    tool_call_id: str,
    model: str = None,
    tokens: dict = None
) -> int:
    """Emit a tool call event."""
    return emit_event(
        run_id,
        EventType.TOOL_CALL,
        {"tool_name": tool_name, "args": args},
        model=model,
        tokens=tokens,
        tool_call_id=tool_call_id,
    )


def emit_tool_result(
    run_id: str,
    tool_name: str,
    result: dict,
    tool_call_id: str,
    status: str = "ok",
) -> int:
    """Emit a tool result event."""
    return emit_event(
        run_id,
        EventType.TOOL_RESULT,
        {"tool_name": tool_name, "result": result, "status": status},
        tool_call_id=tool_call_id,
    )


def emit_assistant_answer(
    run_id: str, 
    content: str, 
    model: str = None, 
    tokens: dict = None,
    cost_eur: float = None
) -> int:
    """Emit an assistant answer event."""
    return emit_event(
        run_id,
        EventType.ASSISTANT_ANSWER,
        {"content": content},
        model=model,
        tokens=tokens,
        cost_eur=cost_eur,
    )


def emit_status_update(run_id: str, status: str, message: str = None) -> int:
    """Emit a status update event."""
    data = {"status": status}
    if message:
        data["message"] = message
    return emit_event(run_id, EventType.STATUS_UPDATE, data)


def emit_error(run_id: str, error: str, details: str = None) -> int:
    """Emit an error event."""
    data = {"error": error}
    if details:
        data["details"] = details
    return emit_event(run_id, EventType.ERROR, data)