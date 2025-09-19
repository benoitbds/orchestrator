import asyncio
import pytest
from types import SimpleNamespace

from agents.handlers import draft_features_from_matches_handler
from orchestrator.models import Document


@pytest.fixture(autouse=True)
def patch_graph():
    yield


def test_draft_features_creates_items(monkeypatch):
    # prepare chunks
    fake_chunks = [
        {"doc_id": 1, "text": "Cas d'usage: gérer le backlog", "embedding": [0.1, 0.2]},
    ]
    monkeypatch.setattr(
        "agents.handlers.crud.get_all_document_chunks_for_project",
        lambda project_id: fake_chunks,
    )
    monkeypatch.setattr(
        "agents.handlers.crud.get_documents",
        lambda project_id: [
            Document(
                id=1,
                project_id=project_id,
                filename="doc.txt",
                content="",
                embedding=None,
                filepath=None,
                status="ANALYZED",
                meta=None,
            )
        ],
    )
    async def fake_embed(q):
        return [0.1, 0.2]

    monkeypatch.setattr("agents.handlers.embed_text", fake_embed)
    monkeypatch.setattr("agents.handlers.cosine_similarity", lambda a, b: 0.9)

    # dummy llm always returns one feature via tool call
    class DummyLLM:
        def __init__(self, *a, **kw):
            pass

        def bind_tools(self, tools):
            return self

        def invoke(self, msgs):
            return SimpleNamespace(
                tool_calls=[
                    {
                        "name": "return_features",
                        "args": {
                            "features": [
                                {
                                    "title": "Gestion du backlog",
                                    "objective": "Obj",
                                    "business_value": "Val",
                                    "acceptance_criteria": ["crit1", "crit2"],
                                    "parent_hint": None,
                                }
                            ]
                        },
                    }
                ]
            )

    monkeypatch.setattr("agents.handlers.ChatOpenAI", DummyLLM)
    created = []

    def fake_create_item(item):
        created.append(item)
        return SimpleNamespace(id=len(created), title=item.title, parent_id=item.parent_id)

    monkeypatch.setattr("agents.handlers.crud.create_item", fake_create_item)
    monkeypatch.setattr("agents.handlers.crud.get_items", lambda project_id, type=None: [])

    res = asyncio.run(draft_features_from_matches_handler({"project_id": 1, "doc_query": "backlog", "k": 1}))
    assert res["ok"] is True
    assert res["items"][0]["title"] == "Gestion du backlog"
    assert created and created[0].title == "Gestion du backlog"


def test_draft_features_no_matches(monkeypatch):
    monkeypatch.setattr(
        "agents.handlers.crud.get_all_document_chunks_for_project",
        lambda project_id: [],
    )
    monkeypatch.setattr(
        "agents.handlers.crud.get_documents",
        lambda project_id: [
            Document(
                id=1,
                project_id=project_id,
                filename="doc.txt",
                content="",
                embedding=None,
                filepath=None,
                status="UPLOADED",
                meta=None,
            )
        ],
    )
    created = {"count": 0}

    def fake_create(_):
        created["count"] += 1
        return None

    monkeypatch.setattr("agents.handlers.crud.create_item", fake_create)
    res = asyncio.run(draft_features_from_matches_handler({"project_id": 1, "doc_query": "none"}))
    assert res["ok"] is False
    assert res["error"] == "NO_MATCHES"
    assert "Document not indexed" in res["message"]
    assert "Run Analyze" in res["message"]
    assert created["count"] == 0


def test_draft_features_fallback(monkeypatch):
    monkeypatch.setattr(
        "agents.handlers.crud.get_all_document_chunks_for_project",
        lambda project_id: [],
    )
    monkeypatch.setattr(
        "agents.handlers.crud.get_documents",
        lambda project_id: [
            Document(
                id=2,
                project_id=project_id,
                filename="doc.txt",
                content="",
                embedding=None,
                filepath=None,
                status="UPLOADED",
                meta=None,
            )
        ],
    )

    async def fake_embed(q):
        return [0.1]

    monkeypatch.setattr("agents.handlers.embed_text", fake_embed)
    monkeypatch.setattr("agents.handlers.cosine_similarity", lambda a, b: 0.9)

    class DummyLLMNoFeatures:
        def __init__(self, *a, **kw):
            pass

        def bind_tools(self, tools):
            return self

        def invoke(self, msgs):
            return SimpleNamespace(tool_calls=[{"name": "return_features", "args": {"features": []}}])

    monkeypatch.setattr("agents.handlers.ChatOpenAI", lambda *a, **kw: DummyLLMNoFeatures())
    doc_content = """
## Exigences fonctionnelles
- Gestion des commandes omnicanal
- Automatiser la facturation
"""
    monkeypatch.setattr(
        "agents.handlers.crud.get_document",
        lambda doc_id: {"content": doc_content, "status": "UPLOADED"},
    )
    created = []

    def fake_create_item(item):
        created.append(item)
        return SimpleNamespace(id=len(created), title=item.title)

    monkeypatch.setattr("agents.handlers.crud.create_item", fake_create_item)
    monkeypatch.setattr("agents.handlers.crud.get_items", lambda project_id, type=None: [])

    res = asyncio.run(
        draft_features_from_matches_handler({"project_id": 1, "doc_query": "x", "k": 2, "fallback_parse_full_doc": True})
    )
    assert res["ok"] is True
    assert res.get("source") == "fallback_parse"
    assert len(res["items"]) == 2
    assert res["items"][0]["title"] == "Gestion des commandes omnicanal"
    assert len(created) == 2
    assert created[0].title == "Gestion des commandes omnicanal"
