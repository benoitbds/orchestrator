"""SQLModel models for agentic orchestration storage."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlmodel import Column, Field, Index, JSON, SQLModel


class Run(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    request_id: Optional[str] = Field(default=None, index=True)
    project_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    status: str = Field(default="running", nullable=False)
    tool_phase: bool = Field(default=False, nullable=False)
    meta: Optional[dict] = Field(default=None, sa_column=Column(JSON))


class AgentSpan(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    run_id: str = Field(foreign_key="run.id", nullable=False)
    agent_name: str
    start_ts: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    end_ts: Optional[datetime] = None
    status: Optional[str] = None
    input_ref: Optional[str] = None
    output_ref: Optional[str] = None
    meta: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    __table_args__ = (Index("idx_agent_span_run_start", "run_id", "start_ts"),)


class Message(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    run_id: str = Field(foreign_key="run.id", nullable=False)
    agent_name: Optional[str] = None
    role: str
    content_ref: Optional[str] = None
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_eur: Optional[float] = None
    ts: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    __table_args__ = (Index("idx_message_run_ts", "run_id", "ts"),)


class ToolCall(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    run_id: str = Field(foreign_key="run.id", nullable=False)
    agent_name: str
    tool_name: str
    input_ref: Optional[str] = None
    ts: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    span_id: Optional[str] = Field(default=None, foreign_key="agentspan.id")

    __table_args__ = (Index("idx_tool_call_run_ts", "run_id", "ts"),)


class ToolResult(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    run_id: str = Field(foreign_key="run.id", nullable=False)
    tool_call_id: str = Field(foreign_key="toolcall.id", nullable=False)
    output_ref: Optional[str] = None
    status: str
    ts: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class BlobRef(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    kind: str
    data: Any = Field(sa_column=Column(JSON))
    sha256: str
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class RunEvent(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    run_id: str = Field(foreign_key="run.id", nullable=False)
    seq: int = Field(nullable=False)
    event_type: str = Field(nullable=False)  # plan, tool_call, tool_result, assistant_answer, status_update
    ts: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    elapsed_ms: Optional[int] = None
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_eur: Optional[float] = None
    tool_call_id: Optional[str] = None
    data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    __table_args__ = (Index("idx_run_event_seq", "run_id", "seq"),)
