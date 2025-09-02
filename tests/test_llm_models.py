import types
import os
import pytest
from agents import planner, writer
from orchestrator import core_loop, crud


def test_planner_llm_model():
    assert planner.llm.model == "gpt-5"


def test_writer_llm_model():
    assert writer.llm_feature.model == "gpt-5"


@pytest.mark.asyncio
async def test_core_loop_uses_gpt5(monkeypatch, tmp_path):
    captured = {}

    class FakeLLM:
        def __init__(self, model, temperature=0):
            captured["model"] = model

        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            return types.SimpleNamespace(content="", tool_calls=[])

    monkeypatch.setenv("OPENAI_MODEL", "gpt-5")
    monkeypatch.setattr(
        core_loop,
        "build_llm",
        lambda provider, **k: (
            FakeLLM(os.getenv("OPENAI_MODEL", "gpt-5.1-mini"))
            if provider == "openai"
            else None
        ),
    )
    monkeypatch.setattr(core_loop, "LC_TOOLS", [])
    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()
    run_id = "model-test"
    crud.create_run(run_id, "obj", 1)
    await core_loop.run_chat_tools("obj", 1, run_id)
    assert captured["model"] == "gpt-5"
