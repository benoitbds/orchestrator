import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport
from api.main import app
from orchestrator import crud

crud.init_db()

transport = ASGIWebSocketTransport(app=app)
BASE_URL = "http://test"

@pytest.mark.asyncio
async def test_ping():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/ping")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_chat_endpoint():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/chat", json={"objective": "demo"})
        body = r.json()
        assert r.status_code == 200
        assert "html" in body and "summary" in body

@pytest.mark.asyncio
async def test_ws_stream():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with aconnect_ws("http://test/stream", ac) as ws:
            await ws.send_json({"objective": "demo"})
            chunk = await ws.receive_json()
            # Le stub renvoie un chunk 'plan'
            assert "plan" in chunk


@pytest.mark.asyncio
async def test_project_and_backlog_endpoints():
    async with AsyncClient(transport=transport, base_url=BASE_URL) as ac:
        # create project
        r = await ac.post("/projects", json={"name": "Test", "description": ""})
        assert r.status_code == 200
        project = r.json()
        # create item
        item_payload = {
            "title": "Epic 1",
            "description": "desc",
            "type": "Epic",
            "project_id": project["id"],
            "parent_id": None,
        }
        r2 = await ac.post(f"/projects/{project['id']}/items", json=item_payload)
        assert r2.status_code == 200
        item = r2.json()
        # fetch items
        r3 = await ac.get(f"/projects/{project['id']}/items")
        assert r3.status_code == 200
        items = r3.json()
        assert len(items) == 1 and items[0]["id"] == item["id"]

