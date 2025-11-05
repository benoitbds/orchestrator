"""Utility script to compare SQLite schema with ORM expectations and run a smoke test."""

from __future__ import annotations

import asyncio
import os
import sqlite3
import sys
import types
from pathlib import Path

os.environ.setdefault("ALLOW_ANON_AUTH", "1")
os.environ.setdefault("PYTEST_CURRENT_TEST", "verify_schema")
os.environ.setdefault("DEFAULT_TEST_UID", "verify-script")
os.environ.setdefault("DEFAULT_TEST_EMAIL", "verify-script@example.com")
os.environ.setdefault("FIREBASE_SERVICE_ACCOUNT_PATH", "")


# Stub Firebase so importing the API does not require external services.
if "firebase_admin" not in sys.modules:
    fake_auth = types.SimpleNamespace(verify_id_token=lambda token: {"uid": "script-user", "email": "script@example.com"})

    firebase_stub = types.SimpleNamespace(_apps=[], auth=fake_auth)

    def _init_app(*_args, **_kwargs):
        firebase_stub._apps.append(object())
        return firebase_stub

    firebase_stub.initialize_app = _init_app
    firebase_stub.credentials = types.SimpleNamespace(Certificate=lambda _path: None)

    sys.modules["firebase_admin"] = firebase_stub
    sys.modules["firebase_admin.credentials"] = firebase_stub.credentials
    sys.modules["firebase_admin.auth"] = fake_auth


from httpx import ASGITransport, AsyncClient

from api import main as api_main  # noqa: E402  (import after firebase stub)
from api.main import app  # noqa: E402
from orchestrator import crud  # noqa: E402
from orchestrator.models import ProjectCreate  # noqa: E402


def _resolve_db_path(url: str) -> Path:
    if url.startswith("sqlite:///"):
        return Path(url.replace("sqlite:///", "", 1)).expanduser().resolve()
    return Path(url).expanduser().resolve()


def dump_schema(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        rows = cursor.fetchall()
        print(f"\nDetected schema in {db_path}:")
        for row in rows:
            name = row["name"]
            print(f"\nTable: {name}")
            cursor.execute(f"PRAGMA table_info('{name}')")
            for col in cursor.fetchall():
                cid, col_name, col_type, notnull, default, pk = col
                default_repr = f" DEFAULT {default}" if default is not None else ""
                key = " PRIMARY KEY" if pk else ""
                nullability = " NOT NULL" if notnull else ""
                print(f"  - {col_name} {col_type}{nullability}{default_repr}{key}")
    finally:
        conn.close()


async def verify_document_pipeline(project_id: int) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
        payload = {"file": ("verify.txt", b"verification content", "text/plain")}
        upload = await client.post(f"/projects/{project_id}/documents", files=payload)
        if upload.status_code != 201:
            raise RuntimeError(f"Upload failed: {upload.status_code} {upload.text}")
        doc = upload.json()

        analyze = await client.post(f"/documents/{doc['id']}/analyze")
        if analyze.status_code != 200:
            raise RuntimeError(f"Analyze failed: {analyze.status_code} {analyze.text}")

        print(
            "\nDocument pipeline OK:",
            f"doc_id={doc['id']}",
            f"status={analyze.json().get('status')}",
        )


async def main() -> None:
    crud.init_db()

    async def _fake_embed_texts(texts, model="text-embedding-3-small"):
        return [[0.0] * 3 for _ in texts]

    api_main.embed_texts = _fake_embed_texts  # type: ignore[attr-defined]

    db_path = _resolve_db_path(crud.DATABASE_URL)
    dump_schema(db_path)

    test_uid = os.environ.get("DEFAULT_TEST_UID", "verify-script")
    project = crud.create_project(ProjectCreate(name="Verification", description=""), user_uid=test_uid)
    await verify_document_pipeline(project.id)


if __name__ == "__main__":
    asyncio.run(main())
