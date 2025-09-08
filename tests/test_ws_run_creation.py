import asyncio
import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport
from api.main import app
from orchestrator import crud

crud.init_db()
transport = ASGIWebSocketTransport(app=app)

@pytest.mark.asyncio
async def test_ws_start_creates_run():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with aconnect_ws("http://test/stream", ac) as ws:
            await ws.send_json({"objective": "demo"})
            first = await ws.receive_json()
            run_id = first["run_id"]
    run = crud.get_run(run_id)
    assert run is not None
