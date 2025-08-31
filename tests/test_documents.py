import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
from api.main import app
from orchestrator import crud
from orchestrator.models import ProjectCreate


def setup_db(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    client = TestClient(app)
    project = crud.create_project(ProjectCreate(name="Test", description=None))
    return client, project


def test_delete_document_removes_chunks_and_file(tmp_path, monkeypatch):
    client, project = setup_db(tmp_path, monkeypatch)
    fp = tmp_path / "doc.txt"
    fp.write_text("hello")
    doc = crud.create_document(project.id, "doc.txt", "content", None, filepath=str(fp))
    crud.create_document_chunks(doc.id, [
        {"text": "c1", "chunk_index": 0, "embedding": [0.1, 0.2]},
        {"text": "c2", "chunk_index": 1, "embedding": [0.3, 0.4]},
    ])

    assert fp.exists()
    resp = client.delete(f"/documents/{doc.id}")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    conn = crud.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE id=?", (doc.id,))
    assert cur.fetchall() == []
    cur.execute("SELECT * FROM document_chunks WHERE doc_id=?", (doc.id,))
    assert cur.fetchall() == []
    conn.close()
    assert not fp.exists()


def test_delete_document_with_missing_file(tmp_path, monkeypatch):
    client, project = setup_db(tmp_path, monkeypatch)
    missing_fp = tmp_path / "missing.txt"
    doc = crud.create_document(project.id, "missing.txt", "content", None, filepath=str(missing_fp))
    crud.create_document_chunks(doc.id, [
        {"text": "only", "chunk_index": 0, "embedding": [0.1]},
    ])
    resp = client.delete(f"/documents/{doc.id}")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    conn = crud.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE id=?", (doc.id,))
    assert cur.fetchall() == []
    cur.execute("SELECT * FROM document_chunks WHERE doc_id=?", (doc.id,))
    assert cur.fetchall() == []
    conn.close()


def test_delete_document_not_found(tmp_path, monkeypatch):
    client, project = setup_db(tmp_path, monkeypatch)
    resp = client.delete("/documents/9999")
    assert resp.status_code == 404
