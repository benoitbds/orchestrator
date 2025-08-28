import uuid
import pytest

from orchestrator import crud
from orchestrator.models import ProjectCreate
from orchestrator.core_loop import run_chat_tools
from orchestrator import core_loop

crud.init_db()


class _Executor:
    def __init__(self, agent, tools, verbose, max_iterations, handle_parsing_errors):
        self.tools = {t.name: t for t in tools}
        self.calls = []

    async def ainvoke(self, inputs, config):
        run_id = config["configurable"]["run_id"]
        project_id = config["configurable"]["project_id"]
        for call in self.calls:
            kwargs = dict(call["args"])
            kwargs.setdefault("project_id", project_id)
            kwargs["run_id"] = run_id
            await self.tools[call["name"]].coroutine(**kwargs)
        return {"output": "done"}


def _setup_executor(monkeypatch, calls):
    def factory(agent, tools, verbose=False, max_iterations=10, handle_parsing_errors=True):
        ex = _Executor(agent, tools, verbose, max_iterations, handle_parsing_errors)
        ex.calls = calls
        return ex

    monkeypatch.setattr(core_loop, "ChatOpenAI", lambda *a, **k: object())
    import langchain.agents as agents_mod
    monkeypatch.setattr(agents_mod, "create_tool_calling_agent", lambda llm, tools, prompt: object())
    monkeypatch.setattr(agents_mod, "AgentExecutor", factory)


@pytest.mark.asyncio
async def test_run_chat_tools_creates_item(monkeypatch, tmp_path):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))

    calls = [{"name": "create_item", "args": {"title": "Feat", "type": "Feature"}}]
    _setup_executor(monkeypatch, calls)

    run_id = str(uuid.uuid4())
    crud.create_run(run_id, "Create", 1)
    await run_chat_tools("Create", 1, run_id)
    items = crud.get_items(project_id=1)
    assert any(it.title == "Feat" for it in items)
