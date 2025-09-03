import uuid
import types
import types
import uuid
import pytest
from sqlmodel import create_engine

from orchestrator import crud
from orchestrator.models import ProjectCreate
from orchestrator.core_loop import run_chat_tools
from orchestrator import core_loop
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


@pytest.mark.asyncio
async def test_run_chat_tools_creates_item(monkeypatch, tmp_path):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    agentic = tmp_path / "agentic.sqlite"
    monkeypatch.setenv("AGENTIC_DB_URL", f"sqlite:///{agentic}")
    ag_db.engine = create_engine(f"sqlite:///{agentic}")
    ag_db.init_db()

    ai_call = ToolCall(
        name="create_item", args={"title": "Feat", "type": "Feature"}, id="0"
    )
    responses = [
        types.SimpleNamespace(content="", tool_calls=[ai_call]),
        types.SimpleNamespace(content="done", tool_calls=[]),
    ]
    monkeypatch.setattr(
        core_loop,
        "build_llm",
        lambda provider, **k: FakeLLM(responses) if provider == "openai" else None,
    )

    run_id = str(uuid.uuid4())
    crud.create_run(run_id, "Create", 1)
    await run_chat_tools("Create", 1, run_id)
    items = crud.get_items(project_id=1)
    assert any(it.title == "Feat" for it in items)
