import types
import json
import sqlite3
import pytest
from sqlmodel import create_engine

from orchestrator import core_loop, crud
from orchestrator.models import ProjectCreate, FeatureCreate, USCreate
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


def init_crud_db(monkeypatch, tmp_path):
    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.CONN = None
    crud.init_db()
    conn = crud.get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            project_id INTEGER,
            objective TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'running',
            html TEXT,
            summary TEXT,
            artifacts TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT,
            request_id TEXT,
            tool_phase INTEGER DEFAULT 0,
            user_uid TEXT,
            meta TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_request ON runs(request_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_user ON runs(user_uid)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS run_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            node TEXT NOT NULL,
            content TEXT,
            ts TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_run_steps_run ON run_steps(run_id, ts)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS run_events (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            ts TEXT NOT NULL DEFAULT (datetime('now')),
            elapsed_ms INTEGER,
            model TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            cost_eur REAL,
            tool_call_id TEXT,
            data TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_run_events_seq ON run_events(run_id, seq)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_spans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            agent_name TEXT,
            label TEXT NOT NULL,
            start_ts TEXT NOT NULL,
            end_ts TEXT NOT NULL,
            ref TEXT,
            meta TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_spans_run ON agent_spans(run_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            agent_name TEXT,
            label TEXT NOT NULL,
            ts TEXT NOT NULL,
            ref TEXT,
            meta TEXT,
            token_count INTEGER DEFAULT 0,
            cost_eur REAL DEFAULT 0
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_run ON messages(run_id, ts)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            agent_name TEXT,
            label TEXT NOT NULL,
            ts TEXT NOT NULL,
            ref TEXT,
            meta TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tool_calls_run ON tool_calls(run_id, ts)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            agent_name TEXT,
            label TEXT NOT NULL,
            ts TEXT NOT NULL,
            ref TEXT,
            meta TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tool_results_run ON tool_results(run_id, ts)"
    )
    conn.commit()
    conn.close()


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

    init_crud_db(monkeypatch, tmp_path)
    setup_agentic_db(monkeypatch, tmp_path)
    llm = FakeLLM(responses)

    async def fake_chain(tools):
        provider = types.SimpleNamespace(
            make_llm=lambda tool_phase=False, tools=None: llm
        )
        return [provider]

    monkeypatch.setattr(core_loop, "_build_provider_chain", fake_chain)

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

    init_crud_db(monkeypatch, tmp_path)
    setup_agentic_db(monkeypatch, tmp_path)
    llm = FakeLLM(responses)

    async def fake_chain(tools):
        provider = types.SimpleNamespace(
            make_llm=lambda tool_phase=False, tools=None: llm
        )
        return [provider]

    monkeypatch.setattr(core_loop, "_build_provider_chain", fake_chain)

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

    init_crud_db(monkeypatch, tmp_path)
    setup_agentic_db(monkeypatch, tmp_path)

    async def fake_chain(tools):
        provider = types.SimpleNamespace(
            make_llm=lambda tool_phase=False, tools=None: FakeLLM(responses)
        )
        return [provider]

    monkeypatch.setattr(core_loop, "_build_provider_chain", fake_chain)

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

    init_crud_db(monkeypatch, tmp_path)
    setup_agentic_db(monkeypatch, tmp_path)

    async def fake_chain(tools):
        provider = types.SimpleNamespace(
            make_llm=lambda tool_phase=False, tools=None: FakeLLM(responses)
        )
        return [provider]

    monkeypatch.setattr(core_loop, "_build_provider_chain", fake_chain)

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

    init_crud_db(monkeypatch, tmp_path)
    setup_agentic_db(monkeypatch, tmp_path)

    run_id = "run-fail"
    crud.create_run(run_id, "obj", 1)
    result = await core_loop.run_chat_tools("obj", 1, run_id)
    assert "boom" in result["html"]
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_run_chat_tools_emits_events(monkeypatch, tmp_path):
    init_crud_db(monkeypatch, tmp_path)
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

    async def fake_chain(tools):
        provider = types.SimpleNamespace(
            make_llm=lambda tool_phase=False, tools=None: FakeLLM(responses)
        )
        return [provider]

    monkeypatch.setattr(core_loop, "_build_provider_chain", fake_chain)

    await core_loop.run_chat_tools("obj", 1, run_id)
    assert events["start"]
    assert events["end"] and events["end"][0][1]["status"] == "ok"
    assert len(events["msg"]) >= 2
    assert events["call"] and events["result"]


@pytest.mark.asyncio
async def test_run_chat_tools_end_span_on_error(monkeypatch, tmp_path):
    init_crud_db(monkeypatch, tmp_path)
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


@pytest.mark.asyncio
async def test_run_chat_tools_skips_bulk_after_draft(monkeypatch, tmp_path):
    draft_calls: list[dict] = []
    bulk_calls: list[dict] = []

    async def draft_tool(args):
        draft_calls.append(args)
        return json.dumps({"ok": True, "items": [{"id": 101, "title": "Feature A"}]})

    async def bulk_tool(args):
        bulk_calls.append(args)
        return json.dumps({"ok": True, "result": {"created_ids": [202]}})

    draft = types.SimpleNamespace(
        name="draft_features_from_matches",
        description="d",
        args_schema=types.SimpleNamespace(__name__="DraftArgs"),
        ainvoke=draft_tool,
    )
    bulk = types.SimpleNamespace(
        name="bulk_create_features",
        description="d",
        args_schema=types.SimpleNamespace(__name__="BulkArgs"),
        ainvoke=bulk_tool,
    )

    tc_draft = ToolCall(
        name="draft_features_from_matches",
        args={"project_id": 1, "doc_query": "spec", "k": 2},
        id="call_draft",
    )
    tc_bulk = ToolCall(
        name="bulk_create_features",
        args={"project_id": 1, "parent_id": 5, "items": [{"title": "Feature A"}]},
        id="call_bulk",
    )

    responses = [
        types.SimpleNamespace(content="", tool_calls=[tc_draft, tc_bulk]),
        types.SimpleNamespace(content="done", tool_calls=[]),
    ]

    async def fake_safe_invoke(providers, messages, tools=None):
        return responses.pop(0)

    async def fake_build_chain(tools):
        return [object()]

    monkeypatch.setattr(core_loop, "safe_invoke_with_fallback", fake_safe_invoke)
    monkeypatch.setattr(core_loop, "_build_provider_chain", fake_build_chain)
    monkeypatch.setattr(core_loop, "LC_TOOLS", [draft, bulk])

    init_crud_db(monkeypatch, tmp_path)
    setup_agentic_db(monkeypatch, tmp_path)

    run_id = "run-skip-bulk"
    crud.create_run(run_id, "obj", 1)
    out = await core_loop.run_chat_tools("obj", 1, run_id)

    assert "done" in out["html"]
    assert len(draft_calls) == 1
    assert bulk_calls == []


@pytest.mark.asyncio
async def test_generate_children_creates_requested_count(monkeypatch, tmp_path):
    init_crud_db(monkeypatch, tmp_path)
    setup_agentic_db(monkeypatch, tmp_path)
    project = crud.create_project(ProjectCreate(name="Proj", description=""))
    parent = crud.create_item(
        FeatureCreate(title="Feature X", description="", project_id=project.id, parent_id=None)
    )

    outputs = [
        {"ok": True, "items": [{"id": 201, "title": "US 1"}, {"id": 202, "title": "US 2"}]},
        {"ok": True, "items": [{"id": 203, "title": "US 3"}]},
    ]

    async def fake_exec(name, run_id, args):
        assert name == "generate_items_from_parent"
        payload = outputs.pop(0)
        for item in payload.get("items", []):
            crud.create_item(
                USCreate(
                    title=item["title"],
                    description="As a persona, I want something.",
                    project_id=project.id,
                    parent_id=parent.id,
                    acceptance_criteria="Given When Then",
                )
            )
        return json.dumps(payload)

    published = []
    monkeypatch.setattr(core_loop.agent_tools, "_exec", fake_exec)
    monkeypatch.setattr(core_loop.stream, "publish", lambda rid, msg: published.append((rid, msg)))

    run_id = "run-gen-children"
    crud.create_run(run_id, "génère 3 US de Feature #{}".format(parent.id), project.id)
    out = await core_loop.run_chat_tools(f"génère 3 US de Feature #{parent.id}", project.id, run_id)

    children = [
        it
        for it in crud.get_items(project.id, type="US")
        if it.parent_id == parent.id
    ]
    assert len(children) == 3
    assert "3/3" in out["html"]
    payload = next(msg for _, msg in published if msg.get("node") == "generate_children")
    assert payload["summary"]["created_count"] == 3
    assert payload["summary"]["target_count"] == 3


@pytest.mark.asyncio
async def test_generate_children_defaults_to_five(monkeypatch, tmp_path):
    init_crud_db(monkeypatch, tmp_path)
    setup_agentic_db(monkeypatch, tmp_path)
    project = crud.create_project(ProjectCreate(name="Proj", description=""))
    parent = crud.create_item(
        FeatureCreate(title="Feature Y", description="", project_id=project.id, parent_id=None)
    )

    payload = {"ok": True, "items": []}

    async def fake_exec(name, run_id, args):
        assert name == "generate_items_from_parent"
        batch = args["n"]
        items = []
        for i in range(batch):
            idx = len(crud.get_items(project.id, type="US")) + 1
            title = f"US Auto {idx}"
            crud.create_item(
                USCreate(
                    title=title,
                    description="As a persona, I want something.",
                    project_id=project.id,
                    parent_id=parent.id,
                    acceptance_criteria="Given When Then",
                )
            )
            items.append({"id": 300 + idx, "title": title})
        payload["items"] = items
        return json.dumps(payload)

    monkeypatch.setattr(core_loop.agent_tools, "_exec", fake_exec)

    run_id = "run-gen-default"
    crud.create_run(run_id, "génère les US de Feature #{}".format(parent.id), project.id)
    await core_loop.run_chat_tools(f"génère les US de Feature #{parent.id}", project.id, run_id)

    children = [
        it
        for it in crud.get_items(project.id, type="US")
        if it.parent_id == parent.id
    ]
    assert len(children) == 5


@pytest.mark.asyncio
async def test_generate_children_handles_no_matches(monkeypatch, tmp_path):
    init_crud_db(monkeypatch, tmp_path)
    setup_agentic_db(monkeypatch, tmp_path)
    project = crud.create_project(ProjectCreate(name="Proj", description=""))
    parent = crud.create_item(
        FeatureCreate(title="Feature Z", description="", project_id=project.id, parent_id=None)
    )

    async def fake_exec(name, run_id, args):
        return json.dumps({"ok": False, "error": "NO_MATCHES", "message": "No relevant docs"})

    monkeypatch.setattr(core_loop.agent_tools, "_exec", fake_exec)
    published = []
    monkeypatch.setattr(core_loop.stream, "publish", lambda rid, msg: published.append((rid, msg)))

    run_id = "run-gen-nomatch"
    crud.create_run(run_id, "génère 4 user stories de Feature #{}".format(parent.id), project.id)
    result = await core_loop.run_chat_tools(f"génère 4 user stories de Feature #{parent.id}", project.id, run_id)

    children = [
        it
        for it in crud.get_items(project.id, type="US")
        if it.parent_id == parent.id
    ]
    assert not children
    assert "No relevant docs" in result["html"]
    payload = next(msg for _, msg in published if msg.get("node") == "generate_children")
    assert payload["summary"]["created_count"] == 0
    assert payload["summary"]["message"] == "No relevant docs"
