import sqlite3
import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from orchestrator import crud
from orchestrator.models import ProjectCreate, FeatureCreate, USCreate
from api.main import app


# ---------- DB migration ----------

def test_init_db_adds_artifacts_column(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db_path))
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE runs (run_id TEXT PRIMARY KEY, project_id INTEGER, objective TEXT, status TEXT, created_at DATETIME, completed_at DATETIME, html TEXT, summary TEXT)"
    )
    conn.commit()
    conn.close()
    crud.init_db()
    conn = sqlite3.connect(db_path)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(runs)")]
    conn.close()
    assert "artifacts" in cols


# ---------- Chat integration ----------

@pytest.mark.asyncio
async def test_chat_creates_item_and_artifact(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db_path))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    transport = ASGITransport(app=app)
    objective = "Crée la feature 'Canal de vente' pour le projet 1"
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/chat", json={"objective": objective})
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]
        run_resp = await ac.get(f"/runs/{run_id}")
    data = run_resp.json()
    assert data["artifacts"]["created_item_id"] > 0
    nodes = [s["node"] for s in data["steps"]]
    assert "tool:create_item" in nodes


@pytest.mark.asyncio
async def test_chat_invalid_parent_records_error(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db_path))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    transport = ASGITransport(app=app)
    objective = "Crée la feature 'Bad' pour le projet 1 dans l'epic 999"
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/chat", json={"objective": objective})
        run_id = resp.json()["run_id"]
        run_resp = await ac.get(f"/runs/{run_id}")
    data = run_resp.json()
    nodes = [s["node"] for s in data["steps"]]
    assert "error" in nodes
    assert data["status"] == "done"
    assert "invalid parent_id" in data["summary"]


@pytest.mark.asyncio
async def test_chat_invalid_hierarchy_records_error(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db_path))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    feature = crud.create_item(FeatureCreate(title="F", description="", project_id=1, parent_id=None))
    us = crud.create_item(USCreate(title="U", description="", project_id=1, parent_id=feature.id))
    transport = ASGITransport(app=app)
    objective = f"Crée la feature 'Bad' pour le projet 1 dans l'US {us.id}"
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/chat", json={"objective": objective})
        run_id = resp.json()["run_id"]
        run_resp = await ac.get(f"/runs/{run_id}")
    data = run_resp.json()
    nodes = [s["node"] for s in data["steps"]]
    assert "error" in nodes
    assert data["status"] == "done"
    assert "invalid hierarchy" in data["summary"]
