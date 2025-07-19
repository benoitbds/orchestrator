import pytest
from httpx import AsyncClient
from api.main import app

@pytest.mark.asyncio
async def test_ping():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/ping")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_chat_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/chat", json={"objective": "demo"})
        body = r.json()
        assert r.status_code == 200
        assert "html" in body and "summary" in body

@pytest.mark.asyncio
async def test_ws_stream():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        async with ac.ws_connect("/stream") as ws:
            await ws.send_json({"objective": "demo"})
            chunk = await ws.receive_json()
            # Le stub renvoie un chunk 'plan'
            assert "plan" in chunk
