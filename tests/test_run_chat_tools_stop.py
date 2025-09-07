import json
import types
import pytest
from sqlmodel import create_engine

from orchestrator import core_loop, crud
from orchestrator.storage import db as ag_db

crud.init_db()


def setup_agentic_db(monkeypatch, tmp_path):
    db_file = tmp_path / "agentic.sqlite"
    monkeypatch.setenv("AGENTIC_DB_URL", f"sqlite:///{db_file}")
    ag_db.engine = create_engine(f"sqlite:///{db_file}")
    ag_db.init_db()


@pytest.mark.asyncio
async def test_stops_after_final_answer(monkeypatch, tmp_path):
    call_count = {"n": 0}

    responses = [
        types.SimpleNamespace(content="final answer", tool_calls=[]),
        types.SimpleNamespace(content="", tool_calls=[{"id": "1", "name": "t", "args": {}}]),
    ]

    async def fake_safe_invoke(providers, messages, tools=None):
        res = responses[call_count["n"]]
        call_count["n"] += 1
        return res

    monkeypatch.setattr(core_loop, "safe_invoke_with_fallback", fake_safe_invoke)

    async def fake_build_chain(tools):
        return [object()]

    monkeypatch.setattr(core_loop, "_build_provider_chain", fake_build_chain)
    tool = types.SimpleNamespace(
        name="t",
        description="d",
        args_schema=types.SimpleNamespace(__name__="S"),
        ainvoke=lambda args: json.dumps({"ok": True}),
    )
    monkeypatch.setattr(core_loop, "LC_TOOLS", [tool])
    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()
    setup_agentic_db(monkeypatch, tmp_path)

    run_id = "run-final"
    crud.create_run(run_id, "obj", 1)
    await core_loop.run_chat_tools("obj", 1, run_id)
    assert call_count["n"] == 1


@pytest.mark.asyncio
async def test_deduplicates_tool_calls(monkeypatch, tmp_path):
    call_count = {"n": 0}
    tool_calls = [{"id": "1", "name": "t", "args": {}}]
    responses = [
        types.SimpleNamespace(content="", tool_calls=tool_calls),
        types.SimpleNamespace(content="", tool_calls=tool_calls),
    ]

    async def fake_safe_invoke(providers, messages, tools=None):
        res = responses[call_count["n"]]
        call_count["n"] += 1
        return res

    tool_invocations = {"n": 0}

    async def fake_tool(args):
        tool_invocations["n"] += 1
        return json.dumps({"ok": True})

    tool = types.SimpleNamespace(
        name="t",
        description="d",
        args_schema=types.SimpleNamespace(__name__="S"),
        ainvoke=fake_tool,
    )

    monkeypatch.setattr(core_loop, "safe_invoke_with_fallback", fake_safe_invoke)

    async def fake_build_chain2(tools):
        return [object()]

    monkeypatch.setattr(core_loop, "_build_provider_chain", fake_build_chain2)
    monkeypatch.setattr(core_loop, "LC_TOOLS", [tool])
    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()
    setup_agentic_db(monkeypatch, tmp_path)

    run_id = "run-loop"
    crud.create_run(run_id, "obj", 1)
    await core_loop.run_chat_tools("obj", 1, run_id)
    assert tool_invocations["n"] == 1
    assert call_count["n"] == 2
