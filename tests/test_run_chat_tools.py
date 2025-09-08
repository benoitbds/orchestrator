import types
import json
import pytest
from sqlmodel import create_engine

from orchestrator import core_loop, crud
from orchestrator.storage import db as ag_db


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


def setup_agentic_db(monkeypatch, tmp_path):
    db_file = tmp_path / "agentic.sqlite"
    monkeypatch.setenv("AGENTIC_DB_URL", f"sqlite:///{db_file}")
    ag_db.engine = create_engine(f"sqlite:///{db_file}")
    ag_db.init_db()


@pytest.mark.asyncio
async def test_run_chat_tools_injects_ids(monkeypatch, tmp_path):
    captured = {}

    async def fake_tool(args):
        captured.update(args)
        return json.dumps({"ok": True})
    schema = types.SimpleNamespace(__name__="S")
    tool = types.SimpleNamespace(
        name="t", description="d", args_schema=schema, ainvoke=fake_tool
    )
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
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(core_loop, "LLM_PROVIDER_ORDER", ["openai"])

    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()
    setup_agentic_db(monkeypatch, tmp_path)

    run_id = "run-inject"
    crud.create_run(run_id, "obj", 1)
    await core_loop.run_chat_tools("obj", 1, run_id)
    assert captured == {"run_id": run_id, "project_id": 1}


@pytest.mark.asyncio
async def test_run_chat_tools_sanitizes_tool_call_args(monkeypatch, tmp_path):
    event_args = {}

    async def fake_tool(args):
        return json.dumps({"ok": True})

    schema = types.SimpleNamespace(__name__="S")
    tool = types.SimpleNamespace(
        name="t", description="d", args_schema=schema, ainvoke=fake_tool
    )
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
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(core_loop, "LLM_PROVIDER_ORDER", ["openai"])

    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()
    setup_agentic_db(monkeypatch, tmp_path)

    def fake_emit_tool_call(run_id, name, args, tool_call_id, model, tokens):
        event_args.update(args)

    monkeypatch.setattr(core_loop.events, "emit_tool_call", fake_emit_tool_call)

    run_id = "run-sanitize"
    crud.create_run(run_id, "obj", 1)
    await core_loop.run_chat_tools("obj", 1, run_id)

    assert event_args == {}


@pytest.mark.asyncio
async def test_run_chat_tools_handles_unknown_tool(monkeypatch, tmp_path):
    ai_call = ToolCall(name="unknown", args={}, id="0")
    responses = [types.SimpleNamespace(content="", tool_calls=[ai_call])]
    monkeypatch.setattr(
        core_loop,
        "build_llm",
        lambda provider, **k: FakeLLM(responses) if provider == "openai" else None,
    )
    dummy = types.SimpleNamespace(
        name="t", description="d", args_schema=types.SimpleNamespace(__name__="S"), ainvoke=lambda a: "{}"
    )
    monkeypatch.setattr(core_loop, "LC_TOOLS", [dummy])

    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()
    setup_agentic_db(monkeypatch, tmp_path)

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
    dummy = types.SimpleNamespace(
        name="t", description="d", args_schema=types.SimpleNamespace(__name__="S"), ainvoke=lambda a: "{}"
    )
    monkeypatch.setattr(core_loop, "LC_TOOLS", [dummy])

    published = {}
    monkeypatch.setattr(
        core_loop.stream, "publish", lambda rid, msg: published.setdefault("m", msg)
    )

    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()
    setup_agentic_db(monkeypatch, tmp_path)

    run_id = "run-sum"
    crud.create_run(run_id, "obj", 1)
    out = await core_loop.run_chat_tools("obj", 1, run_id)
    assert "all good" in out["html"]
    assert published["m"] == {"node": "write", "summary": "all good"}


@pytest.mark.asyncio
async def test_run_chat_tools_stops_after_errors(monkeypatch, tmp_path):
    calls: list[int] = []

    async def failing_tool(args):
        calls.append(1)
        return json.dumps({"ok": False, "error": "boom"})

    tool = types.SimpleNamespace(
        name="t",
        description="d",
        args_schema=types.SimpleNamespace(__name__="S"),
        ainvoke=failing_tool,
    )
    ai_call = ToolCall(name="t", args={}, id="0")
    responses = [
        types.SimpleNamespace(content="", tool_calls=[ai_call]) for _ in range(3)
    ]
    call_count = {"n": 0}

    async def fake_safe_invoke(providers, messages, tools=None):
        res = responses[call_count["n"]]
        call_count["n"] += 1
        return res

    async def fake_build_chain(tools):
        return [object()]

    monkeypatch.setattr(core_loop, "safe_invoke_with_fallback", fake_safe_invoke)
    monkeypatch.setattr(core_loop, "_build_provider_chain", fake_build_chain)
    monkeypatch.setattr(core_loop, "LC_TOOLS", [tool])

    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()
    setup_agentic_db(monkeypatch, tmp_path)

    run_id = "run-fail"
    crud.create_run(run_id, "obj", 1)
    result = await core_loop.run_chat_tools("obj", 1, run_id)
    assert "boom" in result["html"]
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_run_chat_tools_emits_events(monkeypatch, tmp_path):
    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()
    setup_agentic_db(monkeypatch, tmp_path)
    run_id = "run-evt"
    crud.create_run(run_id, "obj", 1)

    events = {"start": [], "end": [], "msg": [], "call": [], "result": [], "blob": []}
    monkeypatch.setattr(
        core_loop,
        "start_span",
        lambda *a, **k: events["start"].append((a, k)) or "span1",
    )
    monkeypatch.setattr(
        core_loop,
        "end_span",
        lambda span_id, **k: events["end"].append((span_id, k)),
    )

    def fake_save_blob(kind, data):
        events["blob"].append((kind, data))
        return f"blob{len(events['blob'])}"

    monkeypatch.setattr(core_loop, "save_blob", fake_save_blob)
    monkeypatch.setattr(
        core_loop,
        "save_message",
        lambda *a, **k: events["msg"].append((a, k)),
    )
    monkeypatch.setattr(
        core_loop,
        "save_tool_call",
        lambda *a, **k: events["call"].append((a, k)) or "call1",
    )
    monkeypatch.setattr(
        core_loop,
        "save_tool_result",
        lambda *a, **k: events["result"].append((a, k)),
    )

    async def fake_tool(args):
        return json.dumps({"ok": True})

    tool = types.SimpleNamespace(
        name="t",
        description="d",
        args_schema=types.SimpleNamespace(__name__="S"),
        ainvoke=fake_tool,
    )
    ai_call = ToolCall(name="t", args={}, id="0")
    responses = [
        types.SimpleNamespace(content="", tool_calls=[ai_call]),
        types.SimpleNamespace(content="done", tool_calls=[]),
    ]
    monkeypatch.setattr(core_loop, "LC_TOOLS", [tool])
    monkeypatch.setattr(
        core_loop,
        "build_llm",
        lambda provider, **k: FakeLLM(responses) if provider == "openai" else None,
    )

    await core_loop.run_chat_tools("obj", 1, run_id)
    assert events["start"]
    assert events["end"] and events["end"][0][1]["status"] == "ok"
    assert len(events["msg"]) >= 2
    assert events["call"] and events["result"]


@pytest.mark.asyncio
async def test_run_chat_tools_end_span_on_error(monkeypatch, tmp_path):
    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()
    setup_agentic_db(monkeypatch, tmp_path)
    run_id = "run-err2"
    crud.create_run(run_id, "obj", 1)

    ended = []
    monkeypatch.setattr(core_loop, "start_span", lambda *a, **k: "spanX")
    monkeypatch.setattr(
        core_loop,
        "end_span",
        lambda span_id, **k: ended.append((span_id, k)),
    )
    monkeypatch.setattr(core_loop, "save_blob", lambda *a, **k: "b")

    async def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(core_loop, "_run_chat_tools_impl", boom)

    with pytest.raises(RuntimeError):
        await core_loop.run_chat_tools("obj", 1, run_id)
    assert ended and ended[0][1]["status"] == "error"

