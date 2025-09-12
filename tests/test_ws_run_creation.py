import asyncio
import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws, WebSocketDisconnect
from httpx_ws.transport import ASGIWebSocketTransport
from api.main import app
from orchestrator import crud
from firebase_admin import auth as fb_auth

crud.init_db()
transport = ASGIWebSocketTransport(app=app)


@pytest.fixture(autouse=True)
def mock_verify(monkeypatch):
    def fake_verify(token):
        assert token == "good"
        return {"uid": "u1"}

    monkeypatch.setattr(fb_auth, "verify_id_token", fake_verify)


@pytest.mark.asyncio
async def test_ws_start_creates_run():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with aconnect_ws("http://test/stream?token=good", ac) as ws:
            await ws.send_json({"objective": "demo"})
            first = await ws.receive_json()
            run_id = first["run_id"]
    run = crud.get_run(run_id)
    assert run is not None


@pytest.mark.asyncio
async def test_ws_requires_token():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with pytest.raises(WebSocketDisconnect) as exc:
            async with aconnect_ws("http://test/stream", ac):
                pass
        assert exc.value.code == 4401
