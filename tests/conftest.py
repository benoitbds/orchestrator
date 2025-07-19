import os
import types, pytest, asyncio

# Provide a fake API key so OpenAI client initialization succeeds during import
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

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
        """Return a structure similar to ``graph.invoke`` output."""
        summary = "Exécution réussie ✅"
        return {
            "render": {
                "html": "<p>todo stub</p>",
                "summary": summary,
                "artifacts": []
            },
            "result": summary,
            "exec_result": {
                "success": True,
                "stdout": "stub\n",
                "stderr": "",
                "artifacts": []
            },
        }

    FakeGraph = types.SimpleNamespace(invoke=fake_invoke, astream=fake_astream)
    monkeypatch.setattr(cl, "graph", FakeGraph)
