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
    Remplace orchestrator.core_loop.graph par une version stub :
    - invoke(...)  → dict minimal {"render": {...}}
    - astream(...) → yield un seul chunk {"plan": {...}}
    """
    import orchestrator.core_loop as cl

    async def fake_astream(state):
        from datetime import datetime, timedelta, timezone
        from orchestrator import crud
        now = datetime.now(timezone.utc)
        steps = ["plan", "execute", "write"]
        for i, name in enumerate(steps):
            start = now + timedelta(seconds=i)
            end = start + timedelta(milliseconds=100)
            crud.record_run_step(state.run_id, name, "success", start, end, "gpt-4o-mini")
            yield {name: {"result": f"{name} done"}}
            await asyncio.sleep(0)

    def fake_invoke(state):
        from datetime import datetime, timedelta, timezone
        from orchestrator import crud
        now = datetime.now(timezone.utc)
        steps = ["plan", "execute", "write"]
        for i, name in enumerate(steps):
            start = now + timedelta(seconds=i)
            end = start + timedelta(milliseconds=100)
            crud.record_run_step(state.run_id, name, "success", start, end, "gpt-4o-mini")
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

    # Also patch the graph imported in the API module
    import api.main as main
    monkeypatch.setattr(main, "graph", FakeGraph)

    import api.ws as ws
    monkeypatch.setattr(ws, "graph", FakeGraph)
