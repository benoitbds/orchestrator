import types
import json
import pytest

from orchestrator import core_loop, crud

crud.init_db()


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


@pytest.mark.asyncio
async def test_run_chat_tools_injects_ids(monkeypatch, tmp_path):
    captured = {}

    async def fake_tool(args):
        captured.update(args)
        return json.dumps({"ok": True})

    tool = types.SimpleNamespace(name="t", ainvoke=fake_tool)
    ai_call = ToolCall(name="t", args={}, id="0")
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

    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()

    run_id = "run-inject"
    crud.create_run(run_id, "obj", 1)
    await core_loop.run_chat_tools("obj", 1, run_id)
    assert captured == {"run_id": run_id, "project_id": 1}


@pytest.mark.asyncio
async def test_run_chat_tools_handles_unknown_tool(monkeypatch, tmp_path):
    ai_call = ToolCall(name="unknown", args={}, id="0")
    responses = [types.SimpleNamespace(content="", tool_calls=[ai_call])]
    monkeypatch.setattr(
        core_loop,
        "build_llm",
        lambda provider, **k: FakeLLM(responses) if provider == "openai" else None,
    )
    monkeypatch.setattr(core_loop, "LC_TOOLS", [])

    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()

    run_id = "run-err"
    crud.create_run(run_id, "obj", 1)
    result = await core_loop.run_chat_tools("obj", 1, run_id)
    assert "Unknown tool" in result["html"]


@pytest.mark.asyncio
async def test_run_chat_tools_returns_summary(monkeypatch, tmp_path):
    responses = [types.SimpleNamespace(content="all good", tool_calls=[])]
    monkeypatch.setattr(
        core_loop,
        "build_llm",
        lambda provider, **k: FakeLLM(responses) if provider == "openai" else None,
    )
    monkeypatch.setattr(core_loop, "LC_TOOLS", [])

    published = {}
    monkeypatch.setattr(
        core_loop.stream, "publish", lambda rid, msg: published.setdefault("m", msg)
    )

    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()

    run_id = "run-sum"
    crud.create_run(run_id, "obj", 1)
    out = await core_loop.run_chat_tools("obj", 1, run_id)
    assert "all good" in out["html"]
    assert published["m"] == {"node": "write", "summary": "all good"}


@pytest.mark.asyncio
async def test_run_chat_tools_stops_after_errors(monkeypatch, tmp_path):
    async def failing_tool(args):
        return json.dumps({"ok": False})

    tool = types.SimpleNamespace(name="t", ainvoke=failing_tool)
    ai_call = ToolCall(name="t", args={}, id="0")
    responses = [
        types.SimpleNamespace(content="", tool_calls=[ai_call]) for _ in range(3)
    ]
    monkeypatch.setattr(
        core_loop,
        "build_llm",
        lambda provider, **k: FakeLLM(responses) if provider == "openai" else None,
    )
    monkeypatch.setattr(core_loop, "LC_TOOLS", [tool])

    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()

    run_id = "run-fail"
    crud.create_run(run_id, "obj", 1)
    result = await core_loop.run_chat_tools("obj", 1, run_id)
    assert "Too many consecutive tool errors" in result["html"]
