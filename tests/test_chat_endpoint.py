import asyncio
import types

import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from orchestrator import crud

crud.init_db()


transport = ASGITransport(app=app)


@pytest.mark.asyncio
async def test_chat_returns_html(monkeypatch):
    """Run completes immediately and returns HTML."""
    from langchain_openai import ChatOpenAI

    def fake_invoke(self, messages):
        return types.SimpleNamespace(content="done", additional_kwargs={})

    monkeypatch.setattr(ChatOpenAI, "bind_tools", lambda self, tools: self)
    monkeypatch.setattr(ChatOpenAI, "invoke", fake_invoke)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/chat", json={"objective": "demo", "project_id": 1})
    data = resp.json()
    assert resp.status_code == 200
    assert data["run_id"] and data["html"]
    run = crud.get_run(data["run_id"])
    assert run["status"] == "done"


@pytest.mark.asyncio
async def test_chat_polls_until_done(monkeypatch):
    """Run finishes after endpoint polls for completion."""

    async def fake_runner(obj, project_id, run_id):
        async def later():
            await asyncio.sleep(0.1)
            crud.finish_run(
                run_id,
                "<p>ok</p>",
                "ok",
                {"created_item_ids": [], "updated_item_ids": [], "deleted_item_ids": []},
            )

        asyncio.create_task(later())

    monkeypatch.setattr("api.main.run_chat_tools", fake_runner)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/chat", json={"objective": "demo", "project_id": 1})
    data = resp.json()
    assert resp.status_code == 200
    assert data["html"] == "<p>ok</p>"
    run = crud.get_run(data["run_id"])
    assert run["status"] == "done"


@pytest.mark.asyncio
async def test_chat_warns_if_not_done(monkeypatch, caplog):
    """Warn and return empty HTML when run never finishes."""

    async def fake_runner(obj, project_id, run_id):
        return None

    async def fast_sleep(_):
        return None

    monkeypatch.setattr("api.main.run_chat_tools", fake_runner)
    monkeypatch.setattr("api.main.asyncio.sleep", fast_sleep)

    with caplog.at_level("WARNING"):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/chat", json={"objective": "demo", "project_id": 1})
    data = resp.json()
    assert resp.status_code == 200
    assert data["html"] == ""
    assert "finished with status" in caplog.text


@pytest.mark.asyncio
async def test_chat_registers_stream(monkeypatch):
    """Endpoint registers stream so clients can attach."""

    registered: dict[str, str] = {}

    def fake_register(rid, loop):
        registered["run_id"] = rid
        return asyncio.Queue()

    async def fake_runner(obj, project_id, run_id):
        crud.finish_run(run_id, "<p>x</p>", "x", {"created_item_ids": [], "updated_item_ids": [], "deleted_item_ids": []})

    monkeypatch.setattr("api.main.stream.register", fake_register)
    monkeypatch.setattr("api.main.run_chat_tools", fake_runner)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/chat", json={"objective": "demo", "project_id": 1})
    data = resp.json()

    assert registered["run_id"] == data["run_id"]

