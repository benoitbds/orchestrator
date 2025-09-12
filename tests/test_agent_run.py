import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from orchestrator import crud
from orchestrator.models import ProjectCreate
from agents import planner

crud.init_db()

transport = ASGITransport(app=app)


@pytest.mark.asyncio
async def test_agent_run_triggers_planner(monkeypatch):
    project = crud.create_project(ProjectCreate(name="P", description=""))
    called = asyncio.Event()

    async def fake_run_objective(*, project_id: int, objective: str):
        assert project_id == project.id
        assert objective == "do something"
        called.set()

    monkeypatch.setattr(planner, "run_objective", fake_run_objective)

    monkeypatch.setattr(
        "backend.app.security.fb_auth.verify_id_token", lambda t: {"uid": "u"}
    )
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/agent/run",
            json={"project_id": project.id, "objective": "do something"},
            headers={"Authorization": "Bearer token"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    await asyncio.wait_for(called.wait(), 1.0)


@pytest.mark.asyncio
async def test_agent_run_project_not_found(monkeypatch):
    monkeypatch.setattr(
        "backend.app.security.fb_auth.verify_id_token", lambda t: {"uid": "u"}
    )
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/agent/run",
            json={"project_id": 999999, "objective": "x"},
            headers={"Authorization": "Bearer token"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_agent_run_missing_objective(monkeypatch):
    monkeypatch.setattr(
        "backend.app.security.fb_auth.verify_id_token", lambda t: {"uid": "u"}
    )
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/agent/run",
            json={"project_id": 1},
            headers={"Authorization": "Bearer token"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_run_objective_creates_run(monkeypatch):
    project = crud.create_project(ProjectCreate(name="P2", description=""))
    captured = {}

    async def fake_run_chat_tools(objective, project_id, run_id):
        captured.update(
            {"objective": objective, "project_id": project_id, "run_id": run_id}
        )

    monkeypatch.setattr(
        "orchestrator.core_loop.run_chat_tools", fake_run_chat_tools
    )

    result = await planner.run_objective(project_id=project.id, objective="demo")

    assert captured["objective"] == "demo"
    assert captured["project_id"] == project.id
    assert result["run_id"] == captured["run_id"]
    assert result["ok"] is True
    run = crud.get_run(result["run_id"])
    assert run is not None
