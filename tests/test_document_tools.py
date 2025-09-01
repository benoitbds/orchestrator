import pytest

from orchestrator import crud
from orchestrator.models import ProjectCreate
from agents.handlers import (
    list_documents_handler,
    search_documents_handler,
    get_document_handler,
)
import agents.handlers as handlers


def setup(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    project = crud.create_project(ProjectCreate(name="Proj", description=None))
    return project


@pytest.mark.asyncio
async def test_list_documents_handler(tmp_path, monkeypatch):
    project = setup(tmp_path, monkeypatch)
    crud.create_document(project.id, "doc.txt", "content", None, filepath=None)
    res = await list_documents_handler({"project_id": project.id})
    assert res["ok"] and len(res["documents"]) == 1


@pytest.mark.asyncio
async def test_get_document_handler(tmp_path, monkeypatch):
    project = setup(tmp_path, monkeypatch)
    doc = crud.create_document(project.id, "doc.txt", "content", None, filepath=None)
    res = await get_document_handler({"doc_id": doc.id})
    assert res["ok"] and res["content"] == "content"
    missing = await get_document_handler({"doc_id": 999})
    assert not missing["ok"]


@pytest.mark.asyncio
async def test_search_documents_handler(tmp_path, monkeypatch):
    project = setup(tmp_path, monkeypatch)
    doc = crud.create_document(project.id, "doc.txt", "full", None, filepath=None)
    crud.create_document_chunks(
        doc.id,
        [
            {"text": "login page", "chunk_index": 0, "embedding": [1.0, 0.0]},
            {"text": "logout", "chunk_index": 1, "embedding": [0.0, 1.0]},
        ],
    )

    monkeypatch.setattr(handlers, "embed_text", lambda q: [1.0, 0.0])
    monkeypatch.setattr(
        handlers,
        "cosine_similarity",
        lambda a, b: sum(x * y for x, y in zip(a, b)),
    )

    res = await search_documents_handler({"project_id": project.id, "query": "login"})
    assert res["ok"] and res["matches"][0]["text"] == "login page"

    empty = await search_documents_handler({"project_id": project.id + 1, "query": "x"})
    assert empty["ok"] and empty["matches"] == []

