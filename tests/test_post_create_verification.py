import json
import types
import pytest
from orchestrator import core_loop, crud, events
from sqlmodel import create_engine
from orchestrator.storage import db as ag_db


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


def setup_agentic_db(monkeypatch, tmp_path):
    db_file = tmp_path / "agentic.sqlite"
    monkeypatch.setenv("AGENTIC_DB_URL", f"sqlite:///{db_file}")
    ag_db.engine = create_engine(f"sqlite:///{db_file}")
    ag_db.init_db()


def test_verify_snapshot_success(monkeypatch):
    class Item:
        def dict(self):
            return {"id": 1, "title": "t", "secret": "x"}

    monkeypatch.setattr(crud, "get_item", lambda i: Item())
    snap = core_loop._verify_and_snapshot_created_item(1)
    assert snap == {"id": 1, "title": "t"}


def test_verify_snapshot_failure(monkeypatch):
    calls = {"n": 0}

    def fake_get(i):
        calls["n"] += 1
        return None

    monkeypatch.setattr(crud, "get_item", fake_get)
    with pytest.raises(ValueError):
        core_loop._verify_and_snapshot_created_item(1)
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_run_chat_tools_attaches_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()
    setup_agentic_db(monkeypatch, tmp_path)
    run_id = "run-snap"
    crud.create_run(run_id, "obj", 1)

    class Item:
        def dict(self):
            return {"id": 1, "title": "Feat"}

    monkeypatch.setattr(crud, "get_item", lambda i: Item())

    async def fake_create(args):
        return json.dumps({"ok": True, "item_id": 1})

    schema = types.SimpleNamespace(__name__="S")
    tool = types.SimpleNamespace(name="create_item", description="d", args_schema=schema, ainvoke=fake_create)
    ai_call = ToolCall(name="create_item", args={}, id="0")
    responses = [
        types.SimpleNamespace(content="", tool_calls=[ai_call]),
        types.SimpleNamespace(content="done", tool_calls=[]),
    ]
    monkeypatch.setattr(
        core_loop,
        "build_llm",
        lambda provider, **k: FakeLLM(responses) if provider == "openai" else None,
    )
    monkeypatch.setattr(core_loop, "LC_TOOLS", [tool])
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(core_loop, "LLM_PROVIDER_ORDER", ["openai"])

    captured = {}
    monkeypatch.setattr(
        events,
        "emit_tool_result",
        lambda run_id, name, result, tool_call_id, status="ok": captured.setdefault("r", result) or 0,
    )

    await core_loop.run_chat_tools("create something", 1, run_id)
    assert captured["r"]["snapshot"]["id"] == 1
