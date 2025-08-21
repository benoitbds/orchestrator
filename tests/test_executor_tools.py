import json
import types
import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from api.main import app
from orchestrator import crud
from orchestrator.models import ProjectCreate, FeatureCreate


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

    monkeypatch.setattr(ChatOpenAI, "invoke", lambda self, messages, tools=None, tool_choice=None: calls.pop(0))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"objective": "Create Feature 'Canal de vente'", "project_id": 1},
        )
        run_id = resp.json()["run_id"]
        run_resp = await ac.get(f"/runs/{run_id}")
        items_resp = await ac.get("/api/items", params={"project_id": 1})

    data = run_resp.json()
    assert data["artifacts"]["created_item_ids"][0] > 0
    nodes = [s["node"] for s in data["steps"]]
    assert "tool:create_item" in nodes
    assert any(it["title"] == "Canal de vente" for it in items_resp.json())


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
    monkeypatch.setattr(ChatOpenAI, "invoke", lambda self, messages, tools=None, tool_choice=None: calls.pop(0))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"objective": "Rename feature", "project_id": 1},
        )
        run_id = resp.json()["run_id"]
        run_resp = await ac.get(f"/runs/{run_id}")
        item_resp = await ac.get(f"/api/items/{feature.id}")

    data = run_resp.json()
    assert data["artifacts"]["updated_item_ids"][0] == feature.id
    nodes = [s["node"] for s in data["steps"]]
    assert "tool:update_item" in nodes
    assert item_resp.json()["title"] == "Canal v2"


@pytest.mark.asyncio
async def test_chat_max_tool_calls(monkeypatch, tmp_path):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))

    from langchain_openai import ChatOpenAI
    def fake_invoke(self, messages, tools=None, tool_choice=None):
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
    monkeypatch.setattr(ChatOpenAI, "invoke", fake_invoke)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"objective": "loop", "project_id": 1},
        )
        run_id = resp.json()["run_id"]
        run_resp = await ac.get(f"/runs/{run_id}")
    data = run_resp.json()
    nodes = [s["node"] for s in data["steps"]]
    assert nodes.count("tool:create_item") == 6
    assert "error" in nodes
    assert "max tool calls" in data["summary"].lower()


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
    monkeypatch.setattr(ChatOpenAI, "invoke", lambda self, messages, tools=None, tool_choice=None: calls.pop(0))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"objective": "bad parent", "project_id": 1},
        )
        run_id = resp.json()["run_id"]
        run_resp = await ac.get(f"/runs/{run_id}")
    data = run_resp.json()
    nodes = [s["node"] for s in data["steps"]]
    assert "tool:create_item" in nodes
    assert "error" in nodes
    assert "invalid parent" in data["summary"].lower()
