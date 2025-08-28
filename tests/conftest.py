import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Provide a fake API key so OpenAI client initialization succeeds during import
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

@pytest.fixture(autouse=True)
def patch_graph(monkeypatch):
    """
    Remplace run_chat_tools par une version simplifiée pour les tests.
    Publie les étapes plan/execute/write et ferme le flux.
    """
    import api.main as main
    import api.ws as ws

    async def fake_run_chat_tools(objective, project_id, run_id):
        from orchestrator import crud, stream
        steps = ["plan", "execute", "write"]
        for name in steps:
            crud.record_run_step(run_id, name, f"{name} done")
            await asyncio.sleep(0)
        stream.close(run_id)
        return {"html": "", "summary": ""}

    monkeypatch.setattr(main, "run_chat_tools", fake_run_chat_tools)
    monkeypatch.setattr(ws, "run_chat_tools", fake_run_chat_tools)

