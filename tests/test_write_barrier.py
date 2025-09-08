import json
import types
import pytest

from orchestrator import core_loop, crud
from orchestrator.storage import db as ag_db
from sqlmodel import create_engine

class ToolCall(dict):
    def __getattr__(self, item):
        return self[item]

class FakeLLM:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0
    def bind_tools(self, tools):
        return self
    def invoke(self, messages):
        res = self.responses[self.calls]
        self.calls += 1
        return res

async def _run_flow(monkeypatch, tmp_path, responses, delete_calls):
    # stub tools
    async def fake_create(args):
        return json.dumps({"ok": True, "item_id": 1})
    async def fake_delete(args):
        delete_calls.append(args)
        return json.dumps({"ok": True, "item_id": args["id"]})
    schema = types.SimpleNamespace(__name__="S")
    create_tool = types.SimpleNamespace(name="create_item", description="d", args_schema=schema, ainvoke=fake_create)
    delete_tool = types.SimpleNamespace(name="delete_item", description="d", args_schema=schema, ainvoke=fake_delete)
    monkeypatch.setattr(core_loop, "LC_TOOLS", [create_tool, delete_tool])

    # fake llm provider
    monkeypatch.setattr(core_loop, "build_llm", lambda provider, **k: FakeLLM(responses) if provider == "openai" else None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(core_loop, "LLM_PROVIDER_ORDER", ["openai"])

    # databases
    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()
    db_file = tmp_path / "agentic.sqlite"
    monkeypatch.setenv("AGENTIC_DB_URL", f"sqlite:///{db_file}")
    ag_db.engine = create_engine(f"sqlite:///{db_file}")
    ag_db.init_db()

    class Item:
        def dict(self):
            return {"id": 1, "title": "t"}

    monkeypatch.setattr(crud, "get_item", lambda i: Item())

    # mute streams/events
    monkeypatch.setattr(core_loop.stream, "publish", lambda *a, **k: None)
    monkeypatch.setattr(core_loop.stream, "close", lambda *a, **k: None)
    monkeypatch.setattr(core_loop.stream, "discard", lambda *a, **k: None)
    monkeypatch.setattr(core_loop.events, "emit_status_update", lambda *a, **k: None)
    monkeypatch.setattr(core_loop.events, "emit_tool_call", lambda *a, **k: None)
    monkeypatch.setattr(core_loop.events, "emit_tool_result", lambda *a, **k: None)
    monkeypatch.setattr(core_loop.events, "emit_assistant_answer", lambda *a, **k: None)
    monkeypatch.setattr(core_loop.events, "cleanup_run", lambda *a, **k: None)

    run_id = "r1"
    crud.create_run(run_id, "delete", 1)
    await core_loop.run_chat_tools("delete", 1, run_id)

@pytest.mark.asyncio
async def test_delete_blocked_without_confirmation(monkeypatch, tmp_path, caplog):
    m_create = types.SimpleNamespace(content="", tool_calls=[ToolCall(name="create_item", args={"type":"US","title":"t","project_id":1}, id="0")])
    m_delete = types.SimpleNamespace(
        content="",
        tool_calls=[
            ToolCall(
                name="delete_item",
                args={"id": 1, "project_id": 1, "type": "US", "reason": "tmp"},
                id="1",
            )
        ],
    )
    m_done = types.SimpleNamespace(content="done", tool_calls=[])
    responses = [m_create, m_delete, m_done]
    delete_calls = []
    with caplog.at_level("WARNING"):
        await _run_flow(monkeypatch, tmp_path, responses, delete_calls)
    assert not delete_calls
    assert "blocked_by_write_barrier" in caplog.text

@pytest.mark.asyncio
async def test_delete_allowed_with_confirmation(monkeypatch, tmp_path):
    m_create = types.SimpleNamespace(content="", tool_calls=[ToolCall(name="create_item", args={"type":"US","title":"t","project_id":1}, id="0")])
    m_delete = types.SimpleNamespace(
        content="",
        tool_calls=[
            ToolCall(
                name="delete_item",
                args={
                    "id": 1,
                    "project_id": 1,
                    "type": "US",
                    "reason": "tmp",
                    "explicit_confirm": True,
                },
                id="1",
            )
        ],
    )
    m_done = types.SimpleNamespace(content="done", tool_calls=[])
    responses = [m_create, m_delete, m_done]
    delete_calls = []
    await _run_flow(monkeypatch, tmp_path, responses, delete_calls)
    assert delete_calls and delete_calls[0]["id"] == 1
