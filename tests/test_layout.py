import os
import pytest
from httpx import AsyncClient
from httpx_ws.transport import ASGIWebSocketTransport

from api.main import app
from orchestrator import crud
from orchestrator.models import ProjectCreate, FeatureCreate


transport = ASGIWebSocketTransport(app=app)


def setup_db():
    if os.path.exists(crud.DATABASE_URL):
        os.remove(crud.DATABASE_URL)
    crud.init_db()


@pytest.mark.asyncio
async def test_layout_get_returns_manual_rows():
    setup_db()
    project = crud.create_project(ProjectCreate(name="p", description=None))
    item1 = crud.create_item(FeatureCreate(title="f1", project_id=project.id))
    item2 = crud.create_item(FeatureCreate(title="f2", project_id=project.id))
    nodes = [
        {"item_id": item1.id, "x": 1.0, "y": 2.0, "pinned": True},
        {"item_id": item2.id, "x": 3.0, "y": 4.0, "pinned": False},
    ]
    crud.upsert_layout(project.id, nodes)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(f"/projects/{project.id}/layout")
        assert r.status_code == 200
        data = {n["item_id"]: n for n in r.json()["nodes"]}
        assert data[item1.id]["x"] == 1.0
        assert data[item1.id]["pinned"] is True
        assert data[item2.id]["y"] == 4.0


@pytest.mark.asyncio
async def test_layout_put_then_get_returns_updated_positions():
    setup_db()
    project = crud.create_project(ProjectCreate(name="p", description=None))
    item = crud.create_item(FeatureCreate(title="f1", project_id=project.id))

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r0 = await ac.get(f"/projects/{project.id}/layout")
        assert r0.status_code == 200
        assert r0.json()["nodes"] == []

        payload = {"nodes": [{"item_id": item.id, "x": 5, "y": 6, "pinned": False}]}
        r1 = await ac.put(f"/projects/{project.id}/layout", json=payload)
        assert r1.status_code == 200
        assert r1.json() == {"ok": True, "count": 1}

        r2 = await ac.get(f"/projects/{project.id}/layout")
        assert r2.json()["nodes"][0]["x"] == 5

        payload2 = {"nodes": [{"item_id": item.id, "x": 7, "y": 8, "pinned": True}]}
        await ac.put(f"/projects/{project.id}/layout", json=payload2)
        r3 = await ac.get(f"/projects/{project.id}/layout")
        node = r3.json()["nodes"][0]
        assert node["x"] == 7 and node["pinned"] is True


@pytest.mark.asyncio
async def test_layout_put_invalid_item():
    setup_db()
    project1 = crud.create_project(ProjectCreate(name="p1", description=None))
    project2 = crud.create_project(ProjectCreate(name="p2", description=None))
    item_other = crud.create_item(FeatureCreate(title="f2", project_id=project2.id))

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {"nodes": [{"item_id": item_other.id, "x": 1, "y": 1, "pinned": False}]}
        r = await ac.put(f"/projects/{project1.id}/layout", json=payload)
        assert r.status_code == 400

