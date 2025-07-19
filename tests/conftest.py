import types
import pytest
import asyncio

@pytest.fixture(autouse=True)
def patch_graph(monkeypatch):
    """
    Remplace orchestrator.core_loop.graph par une version stub :
    - invoke(...)  → dict minimal {"render": {...}}
    - astream(...) → yield un seul chunk {"plan": {...}}
    """
    import orchestrator.core_loop as cl

    async def fake_astream(state):
        yield {"plan": {"plan": {"objective": state.objective}}}
        await asyncio.sleep(0)   # laisse la boucle tourner

    def fake_invoke(state):
        return {
            "render": {
                "html": "<p>stub</p>",
                "summary": "ok",
                "artifacts": []
            }
        }

    FakeGraph = types.SimpleNamespace(invoke=fake_invoke, astream=fake_astream)
    monkeypatch.setattr(cl, "graph", FakeGraph)
