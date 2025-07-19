import pytest
from httpx import AsyncClient, ASGITransport
from httpx_ws import aconnect_ws
from api.main import app

transport = ASGITransport(app=app)
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
        async with aconnect_ws(f"{BASE_URL}/ws", ac) as ws:
            await ws.send_json({"objective": "demo"})
            chunk = await ws.receive_json()
            # Le stub renvoie un chunk 'plan'
            assert "plan" in chunk
