import pytest
from orchestrator import crud
from orchestrator.models import ProjectCreate


def setup_db(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    project = crud.create_project(ProjectCreate(name="Test", description=None))
    return project


def test_document_crud(tmp_path, monkeypatch):
    project = setup_db(tmp_path, monkeypatch)
    doc = crud.create_document(project.id, "file.txt", "content", [0.1, 0.2])
    fetched = crud.get_document(doc.id)
    assert fetched == doc
    docs = crud.get_documents(project.id)
    assert len(docs) == 1 and docs[0] == doc


def test_get_documents_empty(tmp_path, monkeypatch):
    project = setup_db(tmp_path, monkeypatch)
    docs = crud.get_documents(project.id)
    assert docs == []


def test_get_document_not_found(tmp_path, monkeypatch):
    project = setup_db(tmp_path, monkeypatch)
    assert crud.get_document(999) is None


def test_create_document_invalid_filename(tmp_path, monkeypatch):
    project = setup_db(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        crud.create_document(project.id, "", None, None)

