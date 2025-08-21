import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from orchestrator import crud
from orchestrator.models import ProjectCreate, FeatureCreate, USCreate


def reset_db():
    crud.init_db()
    conn = crud.get_db_connection()
    conn.execute("DELETE FROM run_steps")
    conn.execute("DELETE FROM runs")
    conn.execute("DELETE FROM backlog")
    conn.execute("DELETE FROM projects")
    conn.commit()
    conn.close()


@pytest.mark.asyncio
async def test_create_feature_and_run_steps():
    reset_db()
    project = crud.create_project(ProjectCreate(name="P", description=""))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"objective": "Créer la feature 'Accueil'", "project_id": project.id},
        )
        run_id = resp.json()["run_id"]
        run = (await ac.get(f"/runs/{run_id}")).json()
    assert any(s["node"] == "tool:create_item" for s in run["steps"])
    assert run["artifacts"]["created_item_ids"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        items_resp = await ac.get(f"/api/items?project_id={project.id}")
    items = items_resp.json()
    assert any(it["title"] == "Accueil" and it["type"] == "Feature" for it in items)


@pytest.mark.asyncio
async def test_create_feature_unquoted_title():
    reset_db()
    project = crud.create_project(ProjectCreate(name="P", description=""))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"objective": "Créer la feature Accueil", "project_id": project.id},
        )
        run_id = resp.json()["run_id"]
        run = (await ac.get(f"/runs/{run_id}")).json()
    assert any(s["node"] == "tool:create_item" for s in run["steps"])
    assert run["artifacts"]["created_item_ids"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        items_resp = await ac.get(f"/api/items?project_id={project.id}")
    items = items_resp.json()
    assert any(it["title"] == "Accueil" and it["type"] == "Feature" for it in items)


@pytest.mark.asyncio
async def test_create_us_under_feature():
    reset_db()
    project = crud.create_project(ProjectCreate(name="P", description=""))
    parent = crud.create_item(FeatureCreate(title="Checkout", description="", project_id=project.id, parent_id=None))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"objective": "Créer la US 'payer par carte' sous la Feature 'Checkout'", "project_id": project.id},
        )
        run_id = resp.json()["run_id"]
        run = (await ac.get(f"/runs/{run_id}")).json()
    us_id = run["artifacts"]["created_item_ids"][0]
    us = crud.get_item(us_id)
    assert us.parent_id == parent.id


@pytest.mark.asyncio
async def test_update_feature_by_id():
    reset_db()
    project = crud.create_project(ProjectCreate(name="P", description=""))
    feat = crud.create_item(FeatureCreate(title="Home", description="", project_id=project.id, parent_id=None))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"objective": f"Renomme la feature {feat.id} en 'Accueil v2'", "project_id": project.id},
        )
        run_id = resp.json()["run_id"]
        run = (await ac.get(f"/runs/{run_id}")).json()
    assert feat.id in run["artifacts"]["updated_item_ids"]
    updated = crud.get_item(feat.id)
    assert updated.title == "Accueil v2"


@pytest.mark.asyncio
async def test_update_by_lookup_and_ambiguous_error():
    reset_db()
    project = crud.create_project(ProjectCreate(name="P", description=""))
    crud.create_item(FeatureCreate(title="Foo", description="", project_id=project.id, parent_id=None))
    crud.create_item(FeatureCreate(title="Foo", description="", project_id=project.id, parent_id=None))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"objective": "Update Feature 'Foo' title to 'Bar'", "project_id": project.id},
        )
        run_id = resp.json()["run_id"]
        run = (await ac.get(f"/runs/{run_id}")).json()
    assert run["artifacts"]["updated_item_ids"] == []
    assert any(s["node"] == "error" for s in run["steps"])


@pytest.mark.asyncio
async def test_missing_project_id_error():
    reset_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat", json={"objective": "Créer la feature 'Oops'"}
        )
        run_id = resp.json()["run_id"]
        run = (await ac.get(f"/runs/{run_id}")).json()
    assert any(s["node"] == "intent_error" for s in run["steps"])
    assert run["artifacts"]["created_item_ids"] == []


@pytest.mark.asyncio
async def test_parent_not_found():
    reset_db()
    project = crud.create_project(ProjectCreate(name="P", description=""))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"objective": "Créer la US 'Test' sous la Feature 'Inexistante'", "project_id": project.id},
        )
        run_id = resp.json()["run_id"]
        run = (await ac.get(f"/runs/{run_id}")).json()
    assert run["artifacts"]["created_item_ids"] == []
    assert any(s["node"] == "error" for s in run["steps"])


@pytest.mark.asyncio
async def test_invalid_status_error():
    reset_db()
    project = crud.create_project(ProjectCreate(name="P", description=""))
    us = crud.create_item(USCreate(title="Login", description="", project_id=project.id, parent_id=None))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"objective": f"Change status of US {us.id} to Invalid", "project_id": project.id},
        )
        run_id = resp.json()["run_id"]
        run = (await ac.get(f"/runs/{run_id}")).json()
    assert run["artifacts"]["updated_item_ids"] == []
    assert any(s["node"] == "error" for s in run["steps"])
