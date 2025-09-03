import types
import os
import os
import os
import types
import pytest
from sqlmodel import create_engine
from agents import planner, writer
from orchestrator import core_loop, crud
from orchestrator.storage import db as ag_db


def test_planner_llm_model():
    model = getattr(planner.llm, "model_name", getattr(planner.llm, "model", ""))
    assert model.startswith("gpt-")


def test_writer_llm_model():
    model = getattr(
        writer.llm_feature, "model_name", getattr(writer.llm_feature, "model", "")
    )
    assert model.startswith("gpt-")


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
    dummy = types.SimpleNamespace(
        name="t", description="d", args_schema=types.SimpleNamespace(__name__="S"), ainvoke=lambda a: "{}"
    )
    monkeypatch.setattr(core_loop, "LC_TOOLS", [dummy])
    monkeypatch.setattr(crud, "DATABASE_URL", str(tmp_path / "db.sqlite"))
    crud.init_db()
    db_file = tmp_path / "agentic.sqlite"
    monkeypatch.setenv("AGENTIC_DB_URL", f"sqlite:///{db_file}")
    ag_db.engine = create_engine(f"sqlite:///{db_file}")
    ag_db.init_db()
    run_id = "model-test"
    crud.create_run(run_id, "obj", 1)
    await core_loop.run_chat_tools("obj", 1, run_id)
    assert captured["model"] == "gpt-5"
