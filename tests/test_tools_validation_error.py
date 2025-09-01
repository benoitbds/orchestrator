import json
import pytest
from pydantic import BaseModel
import agents.tools as tools


class _Args(BaseModel):
    items: list[int]


@pytest.mark.asyncio
async def test_exec_validation_error_returns_hint(monkeypatch):
    async def handler(args):
        _Args(**args)  # raises if 'items' missing
        return {"ok": True}

    monkeypatch.setitem(tools.HANDLERS, "bulk_create_features", handler)
    recorded = {}

    def fake_record(run_id, step, data, broadcast=False):
        recorded["step"] = step
        recorded["data"] = json.loads(data)

    monkeypatch.setattr(tools.crud, "record_run_step", fake_record)
    monkeypatch.setattr(tools.stream, "publish", lambda *a, **k: None)

    out = await tools._exec("bulk_create_features", "rid", {"project_id": 1, "parent_id": 2})
    data = json.loads(out)
    assert data["error"] == "VALIDATION_ERROR"
    assert "items" in data["expected"]
    assert recorded["step"] == "tool:bulk_create_features:validation_error"


@pytest.mark.asyncio
async def test_exec_unknown_tool(monkeypatch):
    monkeypatch.setattr(tools.crud, "record_run_step", lambda *a, **k: None)
    monkeypatch.setattr(tools.stream, "publish", lambda *a, **k: None)

    out = await tools._exec("does_not_exist", "rid", {})
    data = json.loads(out)
    assert data["ok"] is False
    assert "No handler found" in data["error"]


@pytest.mark.asyncio
async def test_exec_general_exception(monkeypatch):
    async def boom(args):
        raise RuntimeError("boom")

    monkeypatch.setitem(tools.HANDLERS, "boom", boom)
    monkeypatch.setattr(tools.crud, "record_run_step", lambda *a, **k: None)
    monkeypatch.setattr(tools.stream, "publish", lambda *a, **k: None)

    out = await tools._exec("boom", "rid", {})
    data = json.loads(out)
    assert data["ok"] is False
    assert "Tool execution failed" in data["error"]
