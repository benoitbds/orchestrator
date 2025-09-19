import pytest
from orchestrator import crud
from orchestrator.models import ProjectCreate, EpicCreate, FeatureCreate, USCreate
from agents.tools_context import set_current_run_id
from agents.schemas import ensure_acceptance_list
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
async def test_ai_create_marks_pending(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    project = crud.create_project(ProjectCreate(name="Proj", description=""))

    set_current_run_id("run-ai-create")
    try:
        res = await create_item_tool({
            "title": "AI Feature",
            "type": "Feature",
            "project_id": project.id,
        })
    finally:
        set_current_run_id(None)

    assert res["ok"]
    item = crud.get_item(res["item_id"])
    assert item.ia_review_status == "pending"
    assert item.last_modified_by == "ai"
    assert item.ia_last_run_id == "run-ai-create"


@pytest.mark.asyncio
async def test_validate_and_ai_retouch(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    project = crud.create_project(ProjectCreate(name="Proj", description=""))
    epic = crud.create_item(
        EpicCreate(title="Root", description="", project_id=project.id, parent_id=None)
    )
    feature = crud.create_item(
        FeatureCreate(title="Feature", description="", project_id=project.id, parent_id=epic.id)
    )

    set_current_run_id("run-ai")
    try:
        res = await create_item_tool({
            "title": "Story",
            "type": "US",
            "project_id": project.id,
            "parent_id": feature.id,
        })
    finally:
        set_current_run_id(None)

    item_id = res["item_id"]
    crud.validate_item(item_id, "user-1")
    item = crud.get_item(item_id)
    assert item.ia_review_status == "approved"
    assert item.validated_by == "user-1"

    set_current_run_id("run-ai-2")
    try:
        await update_item_tool({"id": item_id, "title": "Story updated"})
    finally:
        set_current_run_id(None)

    item = crud.get_item(item_id)
    assert item.ia_review_status == "pending"


@pytest.mark.asyncio
async def test_bulk_create_features_normalizes_acceptance_criteria(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    project = crud.create_project(ProjectCreate(name="Proj", description=""))
    epic = crud.create_item(
        EpicCreate(title="Epic1", description="", project_id=project.id, parent_id=None)
    )
    res = await bulk_create_features_tool(
        {
            "project_id": project.id,
            "parent_id": epic.id,
            "items": [
                {"title": "String AC", "acceptance_criteria": "  Given then  "},
                {
                    "title": "List AC",
                    "acceptance_criteria": ["First outcome", " Second outcome"],
                },
            ],
        }
    )
    assert res["ok"] is True
    feats = {
        it.title: it
        for it in crud.get_items(project.id, type="Feature")
        if it.parent_id == epic.id
    }
    assert feats["String AC"].acceptance_criteria == "- Given then\n- Cas nominal : valider le comportement attendu."
    assert feats["List AC"].acceptance_criteria == "- First outcome\n- Second outcome"


@pytest.mark.asyncio
async def test_bulk_create_features_parent_mismatch_returns_conflict(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    project_a = crud.create_project(ProjectCreate(name="A", description=""))
    project_b = crud.create_project(ProjectCreate(name="B", description=""))
    other_parent = crud.create_item(
        EpicCreate(title="EpicB", description="", project_id=project_b.id, parent_id=None)
    )
    res = await bulk_create_features_tool(
        {
            "project_id": project_a.id,
            "parent_id": other_parent.id,
            "items": [{"title": "Should fail"}],
        }
    )
    assert res["ok"] is False
    assert res["error"] == "PARENT_PROJECT_MISMATCH"
    assert res.get("status") == 409
    assert not [it for it in crud.get_items(project_a.id, type="Feature")]
    assert not [it for it in crud.get_items(project_b.id, type="Feature") if it.parent_id == other_parent.id]


def test_ensure_acceptance_list_guarantees_two_items():
    lines = ensure_acceptance_list("Unique AC")
    assert len(lines) == 2
    assert lines[0] == "Unique AC"
    assert lines[1] != "Unique AC"

    lines_with_newlines = ensure_acceptance_list("- Premier\n- Premier\nDeuxième")
    assert lines_with_newlines == ["Premier", "Deuxième"]
