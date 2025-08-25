import types
import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Provide a fake API key so OpenAI client initialization succeeds during import
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

@pytest.fixture(autouse=True)
def patch_graph(monkeypatch):
    """
    Remplace orchestrator.core_loop.graph par une version simplifiée :
    - invoke(...)  → dict minimal {"render": {...}}
    - astream(...) → yield un seul chunk {"plan": {...}}
    """
    import orchestrator.core_loop as cl

    async def fake_astream(state):
        from orchestrator import crud
        steps = ["plan", "execute", "write"]
        for name in steps:
            crud.record_run_step(state.run_id, name, f"{name} done")
            yield {name: {"result": f"{name} done"}}
            await asyncio.sleep(0)

    def fake_invoke(state):
        from orchestrator import crud
        steps = ["plan", "execute", "write"]
        for name in steps:
            crud.record_run_step(state.run_id, name, f"{name} done")
        summary = "Exécution réussie ✅"
        artifacts = {"created_item_ids": [], "updated_item_ids": [], "deleted_item_ids": []}
        html = cl._build_html(summary, artifacts)
        return {
            "render": {"html": html, "summary": summary, "artifacts": artifacts},
            "result": summary,
            "exec_result": {
                "success": True,
                "stdout": "done\n",
                "stderr": "",
                "artifacts": []
            },
        }

    FakeGraph = types.SimpleNamespace(invoke=fake_invoke, astream=fake_astream)
    monkeypatch.setattr(cl, "graph", FakeGraph)

    # Also patch the graph imported in the API module
    import api.main as main
    monkeypatch.setattr(main, "graph", FakeGraph, raising=False)
    import api.ws as ws
    monkeypatch.setattr(ws, "graph", FakeGraph)

