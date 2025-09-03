import asyncio
import pytest
from pydantic import BaseModel

import types
import sys

# Provide a minimal stub for the sqlmodel module required by imports in test fixtures
sys.modules.setdefault(
    "sqlmodel",
    types.SimpleNamespace(
        Session=object,
        SQLModel=type("SQLModel", (), {"__init_subclass__": lambda cls, **kw: None}),
        Column=lambda *a, **k: None,
        Field=lambda *a, **k: None,
        Index=lambda *a, **k: None,
        JSON=object,
        create_engine=lambda *a, **k: None,
    ),
)

import agents.tools as tool_mod
from agents.tools_context import set_current_run_id, get_current_run_id


class Dummy(BaseModel):
    pass


@pytest.mark.asyncio
async def test_tool_reads_context_run_id(monkeypatch):
    """Tool should use run_id from contextvars when not provided."""
    captured = {}

    async def fake_exec(name, run_id, args):
        captured["run_id"] = run_id
        captured["ctx"] = get_current_run_id()
        return "ok"

    monkeypatch.setattr(tool_mod, "_exec", fake_exec)

    set_current_run_id("abc")
    tool = tool_mod._mk_tool("t", "desc", Dummy)
    await tool.coroutine()

    assert captured["run_id"] == "abc"
    assert captured["ctx"] == "abc"


@pytest.mark.asyncio
async def test_run_id_context_is_isolated(monkeypatch):
    """Different async tasks should not leak run_id between each other."""
    captured = []

    async def fake_exec(name, run_id, args):
        captured.append((run_id, get_current_run_id()))
        await asyncio.sleep(0)
        return "ok"

    monkeypatch.setattr(tool_mod, "_exec", fake_exec)
    tool = tool_mod._mk_tool("t", "desc", Dummy)

    async def runner(run_id: str):
        set_current_run_id(run_id)
        await asyncio.sleep(0)
        await tool.coroutine()

    await asyncio.gather(runner("one"), runner("two"))

    assert len(captured) == 2
    assert {("one", "one"), ("two", "two")} == set(captured)
