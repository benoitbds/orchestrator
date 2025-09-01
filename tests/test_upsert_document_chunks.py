import pytest
from orchestrator import crud
from orchestrator.models import ProjectCreate


@pytest.fixture
def doc(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    project = crud.create_project(ProjectCreate(name="P", description=None))
    return crud.create_document(project.id, "f.txt", "hello world", None)


def test_upsert_idempotent(doc):
    payload = [(0, "first", [0.1, 0.2]), (1, "second", [0.3, 0.4])]
    assert crud.upsert_document_chunks(doc.id, payload) == 2
    chunks = crud.get_document_chunks(doc.id)
    assert len(chunks) == 2

    # update existing chunk 0
    payload2 = [(0, "updated", [0.9, 0.9])]
    crud.upsert_document_chunks(doc.id, payload2)
    chunks = crud.get_document_chunks(doc.id)
    assert len(chunks) == 2
    chunk0 = [c for c in chunks if c["chunk_index"] == 0][0]
    assert chunk0["text"] == "updated"
    assert chunk0["embedding"] == [0.9, 0.9]


def test_upsert_empty(doc):
    assert crud.upsert_document_chunks(doc.id, []) == 0
