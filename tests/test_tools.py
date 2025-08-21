import pytest
from orchestrator import crud
from orchestrator.models import ProjectCreate, EpicCreate, FeatureCreate
from agents.tools import create_item_tool, update_item_tool, find_item_tool

@pytest.mark.asyncio
async def test_create_item_tool(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    res = await create_item_tool({"title": "Feat", "type": "Feature", "project_id": 1})
    assert res["ok"] is True
    assert res["item_id"] > 0

@pytest.mark.asyncio
async def test_update_item_tool_and_invalid_parent(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    epic = crud.create_item(EpicCreate(title="Ep", description="", project_id=1, parent_id=None))
    feat = crud.create_item(FeatureCreate(title="F", description="", project_id=1, parent_id=epic.id))
    res = await update_item_tool({"id": feat.id, "title": "F2"})
    assert res["ok"] and res["updated_fields"]["title"] == "F2"
    # invalid parent: set feature under itself
    bad = await update_item_tool({"id": feat.id, "parent_id": feat.id})
    assert bad["ok"] is False

@pytest.mark.asyncio
async def test_find_item_tool(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    crud.create_item(FeatureCreate(title="Canal", description="", project_id=1, parent_id=None))
    res = await find_item_tool({"query": "can", "project_id": 1, "type": "Feature"})
    assert res["ok"] and res["matches"][0]["title"] == "Canal"
