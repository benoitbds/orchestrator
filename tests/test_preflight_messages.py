import logging

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from orchestrator.llm.preflight import normalize_history, preflight_validate_messages


@pytest.fixture(autouse=True)
def patch_graph():
    """Override global fixture from conftest; not needed here."""
    yield


def test_assistant_tool_coerced_to_lc():
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
    normalized = normalize_history(history)
    sanitized = preflight_validate_messages(normalized)
    assert sanitized == [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "a1", "type": "tool_call", "name": "x", "args": {}}
            ],
        },
        {"role": "tool", "tool_call_id": "a1", "content": "{}"},
    ]


def test_orphan_tool_dropped(caplog):
    history = [
        {"role": "user", "content": "hi"},
        {"role": "tool", "tool_call_id": "oops", "content": "{}"},
    ]
    normalized = normalize_history(history)
    with caplog.at_level(logging.DEBUG):
        sanitized = preflight_validate_messages(normalized)
    assert sanitized == [history[0]]
    rec = caplog.records[0]
    assert rec.levelno == logging.DEBUG
    assert rec.message == "drop_orphan_tool"


def test_langchain_messages_normalized():
    ai = AIMessage(content="")
    ai.tool_calls = [
        {"id": "a1", "type": "function", "function": {"name": "x", "arguments": {}}}
    ]
    history = [ai, ToolMessage(content="{}", tool_call_id="a1")]
    normalized = normalize_history(history)
    sanitized = preflight_validate_messages(normalized)
    assert sanitized == [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "a1", "type": "tool_call", "name": "x", "args": {}}
            ],
        },
        {"role": "tool", "content": "{}", "tool_call_id": "a1"},
    ]

