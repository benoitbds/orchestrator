import logging
import pytest
from langchain_core.messages import AIMessage

from orchestrator.llm import safe_invoke
from orchestrator.llm.safe_invoke import safe_invoke_with_fallback


@pytest.fixture(autouse=True)
def patch_graph():
    """Override global fixture from conftest; not needed here."""
    yield


class DummyLLM:
    def invoke(self, messages):
        return AIMessage(content="done")


class DummyProvider:
    name = "dummy"

    def make_llm(self, *, tool_phase, tools):
        return DummyLLM()


@pytest.mark.asyncio
async def test_preflight_debug_logged(caplog, monkeypatch):
    history = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "a1", "type": "function", "function": {"name": "x", "arguments": "{}"}}
            ],
        },
        {"role": "tool", "tool_call_id": "a1", "content": "{}"},
    ]

    monkeypatch.setattr(safe_invoke, "in_tool_exchange", False)
    monkeypatch.setattr(safe_invoke._bucket, "take", lambda: True)

    provider = DummyProvider()
    with caplog.at_level(logging.INFO):
        await safe_invoke_with_fallback([provider], history)

    rec = next(r for r in caplog.records if r.message == "preflight_debug")
    payload = rec.__dict__["payload"]
    assert payload["roles"] == ["assistant", "tool"]
    assert payload["assistant_tc_ids"] == ["a1"]
