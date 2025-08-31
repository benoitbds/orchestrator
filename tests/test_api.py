import pytest
import asyncio
import types
import json
from httpx import AsyncClient
from httpx_ws import aconnect_ws, WebSocketDisconnect
from httpx_ws.transport import ASGIWebSocketTransport
from api.main import app
from orchestrator import crud
from orchestrator.models import ProjectCreate
import fitz

crud.init_db()

transport = ASGIWebSocketTransport(app=app)
BASE_URL = "http://test"

@pytest.mark.asyncio
async def test_ping():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/ping")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_ws_stream_new_run():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with aconnect_ws("http://test/stream", ac) as ws:
            await ws.send_json({"objective": "demo"})
            first = await ws.receive_json()
            run_id = first["run_id"]
            assert first["status"] == "started"
            nodes = []
            while True:
                msg = await ws.receive_json()
                if msg.get("status") == "done":
                    assert msg["run_id"] == run_id
                    break
                nodes.append(msg["node"])
            assert nodes == ["plan", "execute", "write"]


@pytest.mark.asyncio
async def test_ws_stream_existing_run_only_new_steps():
    from uuid import uuid4
    from orchestrator import stream as run_stream

    run_id = str(uuid4())
    crud.create_run(run_id, "obj", None)
    queue = run_stream.register(run_id, asyncio.get_event_loop())
    # record a step before connecting
    crud.record_run_step(run_id, "before", "one")

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with aconnect_ws("http://test/stream", ac) as ws:
            await ws.send_json({"run_id": run_id})

            async def later():
                await asyncio.sleep(0.1)
                crud.record_run_step(run_id, "after", "two")
                run_stream.close(run_id)

            asyncio.create_task(later())
            msg = await ws.receive_json()
            assert msg["node"] == "after"
            done = await ws.receive_json()
    assert done["status"] == "done" and done["run_id"] == run_id


@pytest.mark.asyncio
async def test_ws_stream_tool_steps(monkeypatch, tmp_path):
    from uuid import uuid4
    from orchestrator import stream as run_stream
    from orchestrator.core_loop import run_chat_tools
    from orchestrator.models import ProjectCreate
    from orchestrator import core_loop

    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    crud.create_project(ProjectCreate(name="P", description=""))

    class ToolCall(dict):
        def __getattr__(self, item):
            return self[item]

    class FakeLLM:
        def __init__(self, responses):
            self.responses = responses
            self.calls = 0

        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            res = self.responses[self.calls]
            self.calls += 1
            return res

    ai_calls = [
        ToolCall(name="create_item", args={}, id="0"),
        ToolCall(name="update_item", args={"id": 1}, id="1"),
    ]
    responses = [
        types.SimpleNamespace(content="", tool_calls=[ai_calls[0]]),
        types.SimpleNamespace(content="", tool_calls=[ai_calls[1]]),
        types.SimpleNamespace(content="done", tool_calls=[]),
    ]

    monkeypatch.setattr(core_loop, "ChatOpenAI", lambda *a, **k: FakeLLM(responses))

    async def fake_create(args):
        rid = args["run_id"]
        core_loop.stream.publish(rid, {"node": "tool:create_item:request"})
        core_loop.stream.publish(rid, {"node": "tool:create_item:response"})
        return json.dumps({"ok": True, "item_id": 1})

    async def fake_update(args):
        rid = args["run_id"]
        core_loop.stream.publish(rid, {"node": "tool:update_item:request"})
        core_loop.stream.publish(rid, {"node": "tool:update_item:response"})
        return json.dumps({"ok": True})

    create_tool = types.SimpleNamespace(name="create_item", ainvoke=fake_create)
    update_tool = types.SimpleNamespace(name="update_item", ainvoke=fake_update)
    monkeypatch.setattr(core_loop, "LC_TOOLS", [create_tool, update_tool])

    run_id = str(uuid4())
    crud.create_run(run_id, "multi", 1)
    run_stream.register(run_id, asyncio.get_event_loop())

    async def runner():
        await run_chat_tools("multi", 1, run_id)
        run_stream.close(run_id)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with aconnect_ws("http://test/stream", ac) as ws:
            await ws.send_json({"run_id": run_id})
            task = asyncio.create_task(runner())
            steps = []
            while True:
                msg = await ws.receive_json()
                if msg.get("status") == "done":
                    break
                steps.append(msg)

    await task
    nodes = [s["node"] for s in steps]
    assert nodes[-1] == "write"
    assert nodes.count("tool:create_item:request") == 1
    assert nodes.count("tool:create_item:response") == 1
    assert nodes.count("tool:update_item:request") == 1
    assert nodes.count("tool:update_item:response") == 1


@pytest.mark.asyncio
async def test_ws_stream_unknown_run():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with pytest.raises(WebSocketDisconnect) as exc:
            async with aconnect_ws("http://test/stream", ac) as ws:
                await ws.send_json({"run_id": "missing"})
                await ws.receive_json()
        assert exc.value.code == 4404
        assert exc.value.reason == "unknown run"


@pytest.mark.asyncio
async def test_ws_stream_missing_objective():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with pytest.raises(WebSocketDisconnect) as exc:
            async with aconnect_ws("http://test/stream", ac) as ws:
                await ws.send_json({})
                await ws.receive_json()
        assert exc.value.code == 1008
        assert exc.value.reason == "objective required"


@pytest.mark.asyncio
async def test_project_and_backlog_endpoints():
    async with AsyncClient(transport=transport, base_url=BASE_URL) as ac:
        # create project
        r = await ac.post("/projects", json={"name": "Test", "description": ""})
        assert r.status_code == 200
        project = r.json()
        # create item
        item_payload = {
            "title": "Epic 1",
            "description": "desc",
            "type": "Epic",
            "project_id": project["id"],
            "parent_id": None,
        }
        r2 = await ac.post(f"/projects/{project['id']}/items", json=item_payload)
        assert r2.status_code == 200
        item = r2.json()
        # fetch items
    r3 = await ac.get(f"/projects/{project['id']}/items")
    assert r3.status_code == 200
    items = r3.json()
    assert len(items) == 1 and items[0]["id"] == item["id"]


@pytest.mark.asyncio
async def test_feature_proposals_endpoint(monkeypatch):
    """Vérifie l'endpoint POST /api/feature_proposals."""
    from agents.schemas import FeatureProposals, FeatureProposal
    # Stub de l'agent pour renvoyer une réponse contrôlée
    expected = FeatureProposals(
        project_id=1,
        parent_id=2,
        parent_title="Epic demo",
        proposals=[
            FeatureProposal(title="Feat1", description="Desc1"),
            FeatureProposal(title="Feat2", description="Desc2"),
        ],
    )
    monkeypatch.setattr(
        "agents.writer.make_feature_proposals",
        lambda project_id, parent_id, parent_title: expected,
    )

    # Stub de crud.create_item pour simuler l'écriture en BDD
    created = []

    def fake_create_item(item):
        idx = len(created) + 1
        d = {
            "id": idx,
            "title": item.title,
            "description": item.description,
            "type": item.type,
            "project_id": item.project_id,
            "parent_id": item.parent_id,
        }
        created.append(d)
        return d

    from orchestrator import crud
    monkeypatch.setattr(crud, "create_item", fake_create_item)

    async with AsyncClient(transport=transport, base_url=BASE_URL) as ac:
        payload = {
            "project_id": expected.project_id,
            "parent_id": expected.parent_id,
            "parent_title": expected.parent_title,
        }
        r = await ac.post("/api/feature_proposals", json=payload)
        assert r.status_code == 201
        data = r.json()
        # Vérifie que les items ont été créés pour chaque proposition
        assert isinstance(data, list)
        assert len(data) == len(expected.proposals)
        for i, prop in enumerate(expected.proposals):
            assert data[i]["title"] == prop.title
            assert data[i]["description"] == prop.description


@pytest.mark.asyncio
async def test_document_upload_and_listing(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    project = crud.create_project(ProjectCreate(name="P", description=None))

    from orchestrator import embedding_service

    async def fake_embed(*args, **kwargs):
        return []

    monkeypatch.setattr(embedding_service, "embed_document_text", fake_embed)

    async with AsyncClient(transport=transport, base_url=BASE_URL) as ac:
        files = {"file": ("note.txt", b"hello", "text/plain")}
        r = await ac.post(f"/projects/{project.id}/documents", files=files)
        assert r.status_code == 201

        docs = crud.get_documents(project.id)
        assert len(docs) == 1
        assert docs[0].filename == "note.txt"

        rlist = await ac.get(f"/projects/{project.id}/documents")
        assert rlist.status_code == 200
        data = rlist.json()
        assert len(data) == 1 and data[0]["filename"] == "note.txt"


@pytest.mark.asyncio
async def test_pdf_content_extraction(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setattr(crud, "DATABASE_URL", str(db))
    crud.init_db()
    project = crud.create_project(ProjectCreate(name="P", description=None))

    from orchestrator import embedding_service

    async def fake_embed(*args, **kwargs):
        return []

    monkeypatch.setattr(embedding_service, "embed_document_text", fake_embed)

    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "sample pdf text")
    pdf_bytes = pdf.tobytes()
    pdf.close()

    async with AsyncClient(transport=transport, base_url=BASE_URL) as ac:
        files = {"file": ("sample.pdf", pdf_bytes, "application/pdf")}
        r = await ac.post(f"/projects/{project.id}/documents", files=files)
        assert r.status_code == 201
        doc_id = r.json()["id"]

        rcontent = await ac.get(f"/documents/{doc_id}/content")
        assert rcontent.status_code == 200
        assert "sample pdf text" in rcontent.text
