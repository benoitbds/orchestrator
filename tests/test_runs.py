import pytest
import types
import asyncio
from httpx import AsyncClient
import api.main as main
from httpx_ws.transport import ASGIWebSocketTransport
from orchestrator import crud

transport = ASGIWebSocketTransport(app=main.app)

@pytest.mark.asyncio
async def test_run_failure(monkeypatch):
    def failing_invoke(state):
        raise RuntimeError("boom")
    monkeypatch.setattr(main, "graph", types.SimpleNamespace(invoke=failing_invoke))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/chat", json={"objective": "fail"})
        run_id = r.json()["run_id"]
        for _ in range(200):
            r2 = await ac.get(f"/runs/{run_id}")
            data = r2.json()
            if data["status"] != "running":
                break
            await asyncio.sleep(0.1)
    runs = crud.get_runs()
    assert runs and runs[-1].status == "failed"
    assert runs[-1].error
