import os
import pytest
from httpx import AsyncClient
from httpx_ws.transport import ASGIWebSocketTransport
from api.main import app
from orchestrator import crud
from orchestrator.models import ProjectCreate

transport = ASGIWebSocketTransport(app=app)

@pytest.mark.asyncio
async def test_items_crud():
    if os.path.exists(crud.DATABASE_URL):
        os.remove(crud.DATABASE_URL)
    crud.init_db()
    project = crud.create_project(ProjectCreate(name="proj", description=None))

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        epic_payload = {"project_id": project.id, "title": "Epic 1", "type": "Epic"}
        r = await ac.post("/items", json=epic_payload)
        assert r.status_code == 201
        epic = r.json()

        feature_payload = {"project_id": project.id, "title": "Feature", "type": "Feature", "parent_id": epic["id"]}
        rf = await ac.post("/items", json=feature_payload)
        assert rf.status_code == 201
        feature = rf.json()

        story_payload = {"project_id": project.id, "title": "Story", "type": "US", "parent_id": feature["id"]}
        r2 = await ac.post("/items", json=story_payload)
        assert r2.status_code == 201
        story = r2.json()

        rlist = await ac.get(f"/items?project_id={project.id}&type=US")
        assert rlist.status_code == 200
        assert len(rlist.json()) == 1

        rdel = await ac.delete(f"/api/items/{story['id']}")
        assert rdel.status_code == 204
