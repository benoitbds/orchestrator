import pytest
from orchestrator import crud
from orchestrator.models import ProjectCreate, EpicCreate, FeatureCreate, USCreate
from agents.handlers import (
    create_item_tool,
    update_item_tool,
    find_item_tool,
    list_items_tool,
    move_item_tool,
    bulk_create_features_tool,
)

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
async def test_create_item_tool_roundtrip(tmp_path, monkeypatch):
    """Ensure items created via the tool are persisted via CRUD layer."""
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    project = crud.create_project(ProjectCreate(name="Proj", description=""))
    epic = crud.create_item(
        EpicCreate(title="Epic1", description="", project_id=project.id, parent_id=None)
    )
    res = await create_item_tool(
        {
            "title": "Feature test",
            "type": "Feature",
            "project_id": project.id,
            "parent_id": epic.id,
        }
    )
    assert res["ok"] is True
    item_id = res["item_id"]
    created = crud.get_item(item_id)
    assert created.title == "Feature test"
    assert created.type == "Feature"
    assert created.project_id == project.id
    assert created.parent_id == epic.id

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


@pytest.mark.asyncio
async def test_list_items_tool(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    epic = crud.create_item(EpicCreate(title="Epic1", description="", project_id=1, parent_id=None))
    crud.create_item(FeatureCreate(title="FeatA", description="", project_id=1, parent_id=epic.id))
    crud.create_item(FeatureCreate(title="FeatB", description="", project_id=1, parent_id=epic.id))
    all_items = await list_items_tool({"project_id": 1})
    assert all_items["ok"] and len(all_items["result"]) == 3
    filtered = await list_items_tool({"project_id": 1, "type": "Feature"})
    assert filtered["ok"] and len(filtered["result"]) == 2
    queried = await list_items_tool({"project_id": 1, "query": "FeatB"})
    assert queried["ok"] and queried["result"][0]["title"] == "FeatB"


@pytest.mark.asyncio
async def test_move_item_tool(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    epic = crud.create_item(EpicCreate(title="Epic1", description="", project_id=1, parent_id=None))
    feature = crud.create_item(FeatureCreate(title="Feat1", description="", project_id=1, parent_id=epic.id))
    us = crud.create_item(USCreate(title="US1", description="", project_id=1, parent_id=feature.id))
    # same parent no-op
    same = await move_item_tool({"id": feature.id, "new_parent_id": epic.id})
    assert same["ok"] and crud.get_item(feature.id).parent_id == epic.id
    # invalid parent type
    bad_parent = await move_item_tool({"id": feature.id, "new_parent_id": us.id})
    assert not bad_parent["ok"]
    assert crud.get_item(feature.id).parent_id == epic.id
    # cycle detection
    cycle = await move_item_tool({"id": feature.id, "new_parent_id": feature.id})
    assert not cycle["ok"]
    assert crud.get_item(feature.id).parent_id == epic.id


@pytest.mark.asyncio
async def test_bulk_create_features_tool(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    epic = crud.create_item(EpicCreate(title="Epic1", description="", project_id=1, parent_id=None))
    crud.create_item(FeatureCreate(title="Existing", description="", project_id=1, parent_id=epic.id))
    res = await bulk_create_features_tool(
        {
            "project_id": 1,
            "parent_id": epic.id,
            "items": [
                {"title": "New1"},
                {"title": "Existing"},
                {"title": "New1"},
            ],
        }
    )
    assert res["ok"] and len(res["result"]["created_ids"]) == 1
    titles = [it.title for it in crud.get_items(1, type="Feature") if it.parent_id == epic.id]
    assert sorted(titles) == ["Existing", "New1"]


@pytest.mark.asyncio
async def test_bulk_create_features_acceptance_criteria_normalized(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="Proj", description=""))
    epic = crud.create_item(EpicCreate(title="Epic1", description="", project_id=1, parent_id=None))

    expected = "- Given scenario\n- Then result"

    list_payload = {
        "project_id": 1,
        "parent_id": epic.id,
        "items": [
            {
                "title": "Feature from list",
                "acceptance_criteria": ["Given scenario", "Then result"],
            }
        ],
    }
    list_res = await bulk_create_features_tool(list_payload)
    assert list_res["ok"]
    list_id = list_res["result"]["created_ids"][0]
    list_item = crud.get_item(list_id)
    assert list_item.acceptance_criteria == expected

    str_payload = {
        "project_id": 1,
        "parent_id": epic.id,
        "items": [
            {
                "title": "Feature from str",
                "acceptance_criteria": "  - Given scenario\n- Then result  ",
            }
        ],
    }
    str_res = await bulk_create_features_tool(str_payload)
    assert str_res["ok"]
    str_id = str_res["result"]["created_ids"][0]
    str_item = crud.get_item(str_id)
    assert str_item.acceptance_criteria == expected
    assert str_item.acceptance_criteria == list_item.acceptance_criteria
