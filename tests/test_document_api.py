import os
import pytest
from httpx import AsyncClient
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

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        files = {"file": ("note.txt", b"hello", "text/plain")}
        r = await ac.post(f"/projects/{project.id}/documents", files=files)
        assert r.status_code == 201
        doc = r.json()
        assert doc["filename"] == "note.txt"

        rlist = await ac.get(f"/projects/{project.id}/documents")
        assert rlist.status_code == 200
        assert len(rlist.json()) == 1
        assert rlist.json()[0]["id"] == doc["id"]

        rcontent = await ac.get(f"/documents/{doc['id']}/content")
        assert rcontent.status_code == 200
        assert rcontent.text == "hello"


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
