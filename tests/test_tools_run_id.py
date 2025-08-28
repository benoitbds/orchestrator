import pytest
from pydantic import BaseModel
import agents.tools as tool_mod


class Dummy(BaseModel):
    pass


@pytest.mark.asyncio
async def test_tool_uses_global_run_id(monkeypatch):
    captured = {}

    async def fake_exec(name, run_id, args):
        captured["run_id"] = run_id
        return "ok"

    monkeypatch.setattr(tool_mod, "_exec", fake_exec)
    tool_mod.set_current_run("abc")
    tool = tool_mod._mk_tool("t", "desc", Dummy)
    await tool.coroutine()
    assert captured["run_id"] == "abc"
