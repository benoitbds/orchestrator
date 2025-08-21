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
            "/chat",
            json={"objective": "Créer la feature 'Accueil'", "project_id": project.id},
        )
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]
        run = await ac.get(f"/runs/{run_id}")
    run_data = run.json()
    created = run_data["artifacts"]["created_item_ids"]
    assert len(created) == 1
    feature = crud.get_item(created[0])
    assert feature is not None
    assert feature.title == "Accueil"
    assert feature.type == "Feature"
