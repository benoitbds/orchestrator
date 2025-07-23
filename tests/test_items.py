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
    # reset database
    if os.path.exists(crud.DATABASE_URL):
        os.remove(crud.DATABASE_URL)
    crud.init_db()
    project = crud.create_project(ProjectCreate(name="proj", description=None))

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/items", json={"project_id": project.id, "title": "root", "type": "folder"})
        assert r.status_code == 201
        folder1 = r.json()

        r = await ac.post("/items", json={"project_id": project.id, "title": "folder2", "type": "folder"})
        folder2 = r.json()

        r_task = await ac.post("/items", json={"project_id": project.id, "title": "task", "type": "task", "parent_id": folder1["id"]})
        assert r_task.status_code == 201
        task = r_task.json()

        resp = await ac.post("/items", json={"project_id": project.id, "title": "oops", "type": "task", "parent_id": task["id"]})
        assert resp.status_code == 400

        # cannot delete folder with child
        resp = await ac.delete(f"/items/{folder1['id']}")
        assert resp.status_code == 400

        # list items filtered
        r = await ac.get(f"/items?project_id={project.id}&type=task")
        assert r.status_code == 200
        tasks = r.json()
        assert all(it["type"] == "task" for it in tasks)

        # read item with wrong project
        other_proj = crud.create_project(ProjectCreate(name="other", description=None))
        resp = await ac.get(f"/items/{task['id']}?project_id={other_proj.id}")
        assert resp.status_code == 404

        # move task under root -> to check patch
        r = await ac.patch(f"/items/{task['id']}", json={"parent_id": folder2["id"]})
        assert r.status_code == 200
        assert r.json()["parent_id"] == folder2["id"]

        # folder1 now deletable since no child after move
        resp = await ac.delete(f"/items/{folder1['id']}")
        assert resp.status_code == 204

        # folder2 still has child -> cannot delete
        resp = await ac.delete(f"/items/{folder2['id']}")
        assert resp.status_code == 400

        # delete child then folder2
        await ac.delete(f"/items/{task['id']}")
        resp = await ac.delete(f"/items/{folder2['id']}")
        assert resp.status_code == 204
