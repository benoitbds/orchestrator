import asyncio
import json
import importlib
import pytest


async def _sleep_handler(args):
    await asyncio.sleep(0.1)
    return {"ok": True}


@pytest.mark.asyncio
async def test_exec_times_out_with_small_env(monkeypatch):
    monkeypatch.setenv("TOOL_TIMEOUT", "0.05")
    from agents import tools as tools_module
    importlib.reload(tools_module)
    monkeypatch.setattr(tools_module, "HANDLERS", {"sleep": _sleep_handler})
    result = await tools_module._exec("sleep", "run", {})
    data = json.loads(result)
    assert data["ok"] is False
    assert data["error"] == "timeout"


@pytest.mark.asyncio
async def test_exec_succeeds_with_larger_timeout(monkeypatch):
    monkeypatch.setenv("TOOL_TIMEOUT", "0.2")
    from agents import tools as tools_module
    importlib.reload(tools_module)
    monkeypatch.setattr(tools_module, "HANDLERS", {"sleep": _sleep_handler})
    result = await tools_module._exec("sleep", "run", {})
    data = json.loads(result)
    assert data["ok"] is True
