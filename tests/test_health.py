import pytest
from httpx import AsyncClient
from httpx_ws.transport import ASGIWebSocketTransport
from api.main import app
from datetime import datetime

transport = ASGIWebSocketTransport(app=app)

@pytest.mark.asyncio
async def test_health_endpoint_status():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "orchestrator"
    assert "version" in data and data["version"]

@pytest.mark.asyncio
async def test_health_time_is_isoformat():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/health")
    datetime.fromisoformat(res.json()["time"])  # should not raise
