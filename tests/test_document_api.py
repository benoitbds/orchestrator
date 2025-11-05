import os
import pytest
from httpx import AsyncClient
import types
import sys

_fake_credentials = types.SimpleNamespace(Certificate=lambda path: None)
firebase_stub = types.SimpleNamespace(_apps=[], initialize_app=lambda *args, **kwargs: None, credentials=_fake_credentials)
sys.modules.setdefault("firebase_admin", firebase_stub)
sys.modules.setdefault("firebase_admin.credentials", _fake_credentials)

from httpx_ws.transport import ASGIWebSocketTransport
from api.main import app
from orchestrator import crud
from orchestrator.models import ProjectCreate

transport = ASGIWebSocketTransport(app=app)


@pytest.mark.asyncio
async def test_upload_list_and_download(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    project = crud.create_project(ProjectCreate(name="P", description=None))

    monkeypatch.setattr(
        "api.main.chunk_text", lambda text, target_tokens=400, overlap_tokens=60: [text]
    )

    async def fake_embed_texts(texts, model="text-embedding-3-small"):
        return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr("api.main.embed_texts", fake_embed_texts)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        files = {"file": ("note.txt", b"hello", "text/plain")}
        r = await ac.post(f"/projects/{project.id}/documents", files=files)
        assert r.status_code == 201
        doc = r.json()
        assert doc["filename"] == "note.txt"
        assert doc["status"] == "UPLOADED"

        rlist = await ac.get(f"/projects/{project.id}/documents")
        assert rlist.status_code == 200
        items = rlist.json()
        assert len(items) == 1
        assert items[0]["id"] == doc["id"]
        assert items[0]["status"] == "UPLOADED"

        rlist_v2 = await ac.get(f"/documents?project_id={project.id}")
        assert rlist_v2.status_code == 200
        v2_docs = rlist_v2.json()
        assert len(v2_docs) == 1
        assert v2_docs[0]["id"] == doc["id"]
        assert v2_docs[0]["status"] == "UPLOADED"

        rcontent = await ac.get(f"/documents/{doc['id']}/content")
        assert rcontent.status_code == 200
        assert rcontent.text == "hello"

        analyze = await ac.post(f"/documents/{doc['id']}/analyze")
        assert analyze.status_code == 200
        analyzed_payload = analyze.json()
        assert analyzed_payload["status"] == "ANALYZED"
        assert analyzed_payload.get("meta", {}).get("chunk_count") == 1
        total, with_embeddings = crud.document_chunk_stats(doc["id"])
        assert total == 1
        assert with_embeddings == 1


@pytest.mark.asyncio
async def test_upload_document_project_not_found(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        files = {"file": ("note.txt", b"hello", "text/plain")}
        r = await ac.post("/projects/999/documents", files=files)
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_document_content_not_found(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/documents/123/content")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_analyze_document_embedding_error(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    project = crud.create_project(ProjectCreate(name="P", description=None))

    import sys, types
    dummy_doc_processing = types.SimpleNamespace(
        extract_text_from_file=lambda content, filename: content.decode(),
        DocumentParsingError=Exception,
    )
    monkeypatch.setitem(sys.modules, "orchestrator.doc_processing", dummy_doc_processing)

    async def boom(texts):
        raise RuntimeError("boom")

    monkeypatch.setattr("api.main.chunk_text", lambda text, **_: [text])
    monkeypatch.setattr("api.main.embed_texts", boom)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        files = {"file": ("note.txt", b"hello", "text/plain")}
        upload = await ac.post(f"/projects/{project.id}/documents", files=files)
        assert upload.status_code == 201
        payload = upload.json()
        assert payload["status"] == "UPLOADED"

        analyze = await ac.post(f"/documents/{payload['id']}/analyze")
        assert analyze.status_code == 500
        assert analyze.json()["detail"] == "Document analysis failed"

        doc = crud.get_document(payload["id"]) or {}
        assert doc.get("status") == "ERROR"
        meta = doc.get("meta") or {}
        assert isinstance(meta, dict)
        assert meta.get("error") == "boom"
