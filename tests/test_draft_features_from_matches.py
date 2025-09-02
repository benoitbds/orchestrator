import asyncio
import pytest
from types import SimpleNamespace

from agents.handlers import draft_features_from_matches_handler


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
    res = asyncio.run(draft_features_from_matches_handler({"project_id": 1, "doc_query": "none"}))
    assert res["ok"] and res["items"] == []


def test_draft_features_fallback(monkeypatch):
    fake_chunks = [
        {"doc_id": 2, "text": "Périmètre fonctionnel", "embedding": [0.1]},
    ]
    monkeypatch.setattr(
        "agents.handlers.crud.get_all_document_chunks_for_project",
        lambda project_id: fake_chunks,
    )
    async def fake_embed(q):
        return [0.1]

    monkeypatch.setattr("agents.handlers.embed_text", fake_embed)
    monkeypatch.setattr("agents.handlers.cosine_similarity", lambda a, b: 0.9)

    class DummyLLMFallback:
        def __init__(self, *a, **kw):
            self.calls = 0

        def bind_tools(self, tools):
            return self

        def invoke(self, msgs):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(tool_calls=[{"name": "return_features", "args": {"features": []}}])
            return SimpleNamespace(
                tool_calls=[
                    {
                        "name": "return_features",
                        "args": {
                            "features": [
                                {
                                    "title": "Analyse",
                                    "objective": "Obj",
                                    "business_value": "Val",
                                    "acceptance_criteria": ["c1", "c2"],
                                    "parent_hint": None,
                                }
                            ]
                        },
                    }
                ]
            )

    dummy = DummyLLMFallback()
    monkeypatch.setattr("agents.handlers.ChatOpenAI", lambda *a, **kw: dummy)
    monkeypatch.setattr(
        "agents.handlers.crud.get_document",
        lambda doc_id: {"content": "Texte complet"},
    )
    created = []
    monkeypatch.setattr(
        "agents.handlers.crud.create_item",
        lambda item: created.append(item) or SimpleNamespace(id=len(created), title=item.title),
    )
    monkeypatch.setattr("agents.handlers.crud.get_items", lambda project_id, type=None: [])

    res = asyncio.run(draft_features_from_matches_handler({"project_id": 1, "doc_query": "x", "k": 1}))
    assert res["ok"] and res["items"][0]["title"] == "Analyse"
    assert len(created) == 1
