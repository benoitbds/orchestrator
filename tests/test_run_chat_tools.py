import types
import pytest

from orchestrator import core_loop, crud

crud.init_db()


class _FakeExecutor:
    def __init__(self, agent, tools, verbose, max_iterations, handle_parsing_errors):
        self.tools = tools

    async def ainvoke(self, inputs, config):
        run_id = config["configurable"]["run_id"]
        project_id = config["configurable"]["project_id"]
        await self.tools[0].coroutine(run_id=run_id, project_id=project_id)
        return {"output": "done"}


class _ErrorExecutor:
    def __init__(self, *a, **k):
        pass

    async def ainvoke(self, inputs, config):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_run_chat_tools_injects_ids(monkeypatch):
    captured = {}

    async def fake_tool(run_id: str, project_id: int | None = None):
        captured["run_id"] = run_id
        captured["project_id"] = project_id
        return "ok"

    tool = types.SimpleNamespace(name="t", coroutine=fake_tool)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(core_loop, "ChatOpenAI", lambda *a, **k: object())
    import langchain.agents as agents_mod
    monkeypatch.setattr(agents_mod, "create_tool_calling_agent", lambda llm, tools, prompt: object())
    monkeypatch.setattr(agents_mod, "AgentExecutor", _FakeExecutor)
    import agents.tools as tool_mod
    monkeypatch.setattr(tool_mod, "TOOLS", [tool])

    run_id = "run-inject"
    crud.create_run(run_id, "obj", 1)
    await core_loop.run_chat_tools("obj", 1, run_id)
    assert captured == {"run_id": run_id, "project_id": 1}


@pytest.mark.asyncio
async def test_run_chat_tools_handles_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(core_loop, "ChatOpenAI", lambda *a, **k: object())
    import langchain.agents as agents_mod
    monkeypatch.setattr(agents_mod, "create_tool_calling_agent", lambda llm, tools, prompt: object())
    monkeypatch.setattr(agents_mod, "AgentExecutor", _ErrorExecutor)
    import agents.tools as tool_mod
    monkeypatch.setattr(tool_mod, "TOOLS", [])

    run_id = "run-err"
    crud.create_run(run_id, "obj", 1)
    result = await core_loop.run_chat_tools("obj", 1, run_id)
    assert "Agent error" in result["html"]


@pytest.mark.asyncio
async def test_run_chat_tools_returns_summary(monkeypatch):
    class _SummaryExecutor(_FakeExecutor):
        async def ainvoke(self, inputs, config):
            return {"output": "all good"}

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(core_loop, "ChatOpenAI", lambda *a, **k: object())
    import langchain.agents as agents_mod
    monkeypatch.setattr(agents_mod, "create_tool_calling_agent", lambda llm, tools, prompt: object())
    monkeypatch.setattr(agents_mod, "AgentExecutor", _SummaryExecutor)
    import agents.tools as tool_mod
    monkeypatch.setattr(tool_mod, "TOOLS", [])

    published = {}
    monkeypatch.setattr(core_loop.stream, "publish", lambda rid, msg: published.setdefault("m", msg))

    run_id = "run-sum"
    crud.create_run(run_id, "obj", 1)
    out = await core_loop.run_chat_tools("obj", 1, run_id)
    assert "all good" in out["html"]
    assert published["m"] == {"node": "write", "summary": "all good"}
