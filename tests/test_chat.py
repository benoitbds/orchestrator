import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from orchestrator import crud
from orchestrator.models import ProjectCreate


@pytest.mark.asyncio
async def test_chat_creates_feature():
    crud.init_db()
    conn = crud.get_db_connection()
    conn.execute("DELETE FROM run_steps")
    conn.execute("DELETE FROM runs")
    conn.execute("DELETE FROM backlog")
    conn.execute("DELETE FROM projects")
    conn.commit()
    conn.close()

    project = crud.create_project(ProjectCreate(name="Proj", description=""))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat", json={"objective": "Crée la feature entête", "project_id": project.id}
        )
    assert resp.status_code == 200
    data = resp.json()
    created = data["artifacts"]["created_item_ids"]
    assert len(created) == 1
    feature = crud.get_item(created[0])
    assert feature is not None
    assert feature.title == "Crée la feature entête"
    assert feature.type == "Feature"
