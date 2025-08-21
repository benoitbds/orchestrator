import json
import types
import pytest
import types
import json
import uuid
import pytest

from orchestrator import crud
from orchestrator.models import ProjectCreate, FeatureCreate
from orchestrator.core_loop import run_chat_tools


@pytest.mark.asyncio
async def test_chat_creates_item(monkeypatch, tmp_path):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))

    from langchain_openai import ChatOpenAI

    calls = [
        types.SimpleNamespace(
            content="",
            additional_kwargs={
                "tool_calls": [
                    {
                        "id": "1",
                        "type": "function",
                        "function": {
                            "name": "create_item",
                            "arguments": json.dumps(
                                {
                                    "title": "Canal de vente",
                                    "type": "Feature",
                                    "project_id": 1,
                                }
                            ),
                        },
                    }
                ]
            },
        ),
        types.SimpleNamespace(content="done", additional_kwargs={}),
    ]
    monkeypatch.setattr(ChatOpenAI, "bind_tools", lambda self, tools: self)
    monkeypatch.setattr(ChatOpenAI, "invoke", lambda self, messages: calls.pop(0))

    run_id = str(uuid.uuid4())
    crud.create_run(run_id, "Create Feature 'Canal de vente'", 1)
    await run_chat_tools("Create Feature 'Canal de vente'", 1, run_id)
    run = crud.get_run(run_id)
    assert run["artifacts"]["created_item_ids"][0] > 0
    nodes = [s["node"] for s in run["steps"]]
    assert "tool:create_item" in nodes
    items = crud.get_items(project_id=1)
    assert any(it.title == "Canal de vente" for it in items)


@pytest.mark.asyncio
async def test_chat_updates_item(monkeypatch, tmp_path):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    feature = crud.create_item(FeatureCreate(title="Canal", description="", project_id=1, parent_id=None))

    from langchain_openai import ChatOpenAI

    calls = [
        types.SimpleNamespace(
            content="",
            additional_kwargs={
                "tool_calls": [
                    {
                        "id": "1",
                        "type": "function",
                        "function": {
                            "name": "update_item",
                            "arguments": json.dumps({"id": feature.id, "title": "Canal v2"}),
                        },
                    }
                ]
            },
        ),
        types.SimpleNamespace(content="done", additional_kwargs={}),
    ]
    monkeypatch.setattr(ChatOpenAI, "bind_tools", lambda self, tools: self)
    monkeypatch.setattr(ChatOpenAI, "invoke", lambda self, messages: calls.pop(0))

    run_id = str(uuid.uuid4())
    crud.create_run(run_id, "Rename feature", 1)
    await run_chat_tools("Rename feature", 1, run_id)
    run = crud.get_run(run_id)
    assert run["artifacts"]["updated_item_ids"][0] == feature.id
    nodes = [s["node"] for s in run["steps"]]
    assert "tool:update_item" in nodes
    item = crud.get_item(feature.id)
    assert item.title == "Canal v2"


@pytest.mark.asyncio
async def test_chat_max_tool_calls(monkeypatch, tmp_path):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))

    from langchain_openai import ChatOpenAI

    def fake_invoke(self, messages):
        return types.SimpleNamespace(
            content="",
            additional_kwargs={
                "tool_calls": [
                    {
                        "id": "1",
                        "type": "function",
                        "function": {
                            "name": "create_item",
                            "arguments": json.dumps(
                                {
                                    "title": "X",
                                    "type": "Feature",
                                    "project_id": 1,
                                }
                            ),
                        },
                    }
                ]
            },
        )

    monkeypatch.setattr(ChatOpenAI, "bind_tools", lambda self, tools: self)
    monkeypatch.setattr(ChatOpenAI, "invoke", fake_invoke)

    run_id = str(uuid.uuid4())
    crud.create_run(run_id, "loop", 1)
    await run_chat_tools("loop", 1, run_id)
    run = crud.get_run(run_id)
    nodes = [s["node"] for s in run["steps"]]
    assert nodes.count("tool:create_item") == 6
    assert "error" in nodes
    assert "max tool calls" in run["summary"].lower()


@pytest.mark.asyncio
async def test_handler_error(monkeypatch, tmp_path):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))

    from langchain_openai import ChatOpenAI

    calls = [
        types.SimpleNamespace(
            content="",
            additional_kwargs={
                "tool_calls": [
                    {
                        "id": "1",
                        "type": "function",
                        "function": {
                            "name": "create_item",
                            "arguments": json.dumps(
                                {
                                    "title": "Bad",
                                    "type": "Feature",
                                    "project_id": 1,
                                    "parent_id": 999,
                                }
                            ),
                        },
                    }
                ]
            },
        ),
        types.SimpleNamespace(content="Invalid parent", additional_kwargs={}),
    ]
    monkeypatch.setattr(ChatOpenAI, "bind_tools", lambda self, tools: self)
    monkeypatch.setattr(ChatOpenAI, "invoke", lambda self, messages: calls.pop(0))

    run_id = str(uuid.uuid4())
    crud.create_run(run_id, "bad parent", 1)
    await run_chat_tools("bad parent", 1, run_id)
    run = crud.get_run(run_id)
    nodes = [s["node"] for s in run["steps"]]
    assert "tool:create_item" in nodes
    assert "error" in nodes
    assert "invalid parent" in run["summary"].lower()
