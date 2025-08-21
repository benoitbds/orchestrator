import sqlite3
import json
import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from api.main import app
from orchestrator import crud
from orchestrator.models import ProjectCreate, FeatureCreate


# ---------- DB migration ----------

def test_init_db_artifacts_column_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db_path))
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE runs (run_id TEXT PRIMARY KEY, project_id INTEGER, objective TEXT, status TEXT, created_at DATETIME, completed_at DATETIME, html TEXT, summary TEXT)"
    )
    conn.commit()
    conn.close()
    # First migration adds the column, second call should not fail
    crud.init_db()
    crud.init_db()
    conn = sqlite3.connect(db_path)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(runs)")]
    conn.close()
    assert "artifacts" in cols


# ---------- Chat flows ----------

@pytest.mark.asyncio
async def test_chat_create_flow(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db_path))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"objective": "Créer la feature 'Canal de vente'", "project_id": 1},
        )
        run_id = resp.json()["run_id"]
        run_resp = await ac.get(f"/runs/{run_id}")
        items_resp = await ac.get("/api/items", params={"project_id": 1})
    data = run_resp.json()
    assert data["status"] == "done"
    assert data["artifacts"]["created_item_id"] > 0
    nodes = [s["node"] for s in data["steps"]]
    assert "tool:create_item" in nodes
    assert any(it["title"] == "Canal de vente" for it in items_resp.json())


@pytest.mark.asyncio
async def test_chat_update_flow(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db_path))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    feature = crud.create_item(
        FeatureCreate(title="Canal de vente", description="", project_id=1, parent_id=None)
    )
    transport = ASGITransport(app=app)
    objective = f"Modifie le titre de la feature {feature.id} en 'Canal de vente v2'"
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/chat",
            json={"objective": objective, "project_id": 1},
        )
        run_id = resp.json()["run_id"]
        run_resp = await ac.get(f"/runs/{run_id}")
        item_resp = await ac.get(f"/api/items/{feature.id}")
    data = run_resp.json()
    assert data["artifacts"]["updated_item_id"] == feature.id
    nodes = [s["node"] for s in data["steps"]]
    assert "tool:update_item" in nodes
    assert item_resp.json()["title"] == "Canal de vente v2"


@pytest.mark.asyncio
async def test_chat_missing_project_records_error(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db_path))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/chat", json={"objective": "Créer la feature 'X'"})
        run_id = resp.json()["run_id"]
        run_resp = await ac.get(f"/runs/{run_id}")
    data = run_resp.json()
    nodes = [s["node"] for s in data["steps"]]
    assert "error" in nodes
    assert data["status"] == "done"
    assert "project_id" in data["summary"].lower()
