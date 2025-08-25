import json
import types

import pytest

from orchestrator import core_loop, crud

crud.init_db()


class _FakeChatWithTool:
    def __init__(self, *args, **kwargs):
        self._calls = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self._calls += 1
        if self._calls == 1:
            return types.SimpleNamespace(
                content="",
                additional_kwargs={
                    "tool_calls": [
                        {
                            "id": "1",
                            "function": {
                                "name": "create_item",
                                "arguments": json.dumps(
                                    {
                                        "title": "t",
                                        "type": "Epic",
                                        "project_id": 1,
                                        "secret": "sh",
                                    }
                                ),
                            },
                        }
                    ]
                },
            )
        return types.SimpleNamespace(content="done", additional_kwargs={})


class _FakeChatNoTool:
    def __init__(self, *args, **kwargs):
        pass

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        return types.SimpleNamespace(content="done", additional_kwargs={})


@pytest.mark.asyncio
async def test_run_chat_tools_logs_tool_execution(monkeypatch, caplog):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(core_loop, "ChatOpenAI", _FakeChatWithTool)

    async def fake_run_tool(name, args):
        return {"ok": True, "item_id": 1}

    monkeypatch.setattr(core_loop, "_run_tool", fake_run_tool)

    caplog.set_level("INFO")
    result = await core_loop.run_chat_tools("do", 1, "run1")
    assert result["html"]
    assert "FULL-AGENT MODE: starting run_chat_tools(project_id=1)" in caplog.text
    assert "OPENAI_API_KEY set: True" in caplog.text
    assert "TOOLS loaded:" in caplog.text
    assert "Model bound to" in caplog.text
    assert "LLM tool_calls:" in caplog.text
    assert "DISPATCH tool=create_item" in caplog.text


@pytest.mark.asyncio
async def test_run_chat_tools_logs_final_only(monkeypatch, caplog):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(core_loop, "ChatOpenAI", _FakeChatNoTool)
    caplog.set_level("INFO")
    result = await core_loop.run_chat_tools("do", 1, "run2")
    assert result["html"]
    assert "LLM tool_calls: None" in caplog.text


@pytest.mark.asyncio
async def test_run_chat_tools_logs_api_key_missing(monkeypatch, caplog):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(core_loop, "ChatOpenAI", _FakeChatNoTool)
    caplog.set_level("INFO")
    await core_loop.run_chat_tools("do", 1, "run3")
    assert "OPENAI_API_KEY set: False" in caplog.text
