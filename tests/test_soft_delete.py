import pytest
from orchestrator import crud
from orchestrator.models import EpicCreate, ProjectCreate


def _setup_db(monkeypatch, tmp_path):
    db = tmp_path / 'db.sqlite'
    monkeypatch.setattr(crud, 'DATABASE_URL', str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name='P', description=''))


def test_soft_delete_marks_item_deleted(monkeypatch, tmp_path):
    _setup_db(monkeypatch, tmp_path)
    item = crud.create_item(EpicCreate(title='A', description='', project_id=1, parent_id=None))
    assert not item.is_deleted
    crud.delete_item(item.id)
    deleted = crud.get_item(item.id)
    assert deleted.is_deleted


def test_list_items_excludes_deleted(monkeypatch, tmp_path):
    _setup_db(monkeypatch, tmp_path)
    a = crud.create_item(EpicCreate(title='A', description='', project_id=1, parent_id=None))
    b = crud.create_item(EpicCreate(title='B', description='', project_id=1, parent_id=None))
    crud.delete_item(a.id)
    items = crud.get_items(1)
    ids = {i.id for i in items}
    assert a.id not in ids and b.id in ids
