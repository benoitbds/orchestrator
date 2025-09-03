import json
import logging
import pytest
from orchestrator.llm.preflight import preflight_validate_messages


@pytest.fixture(autouse=True)
def patch_graph():
    """Override global fixture from conftest; not needed here."""
    yield


def test_valid_sequence_unchanged():
    msgs = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "a1", "type": "function", "function": {"name": "x", "arguments": "{}"}}
            ],
        },
        {"role": "tool", "tool_call_id": "a1", "content": "{}"},
    ]
    out = preflight_validate_messages(msgs)
    assert out == msgs
    assert out is not msgs


def test_invalid_tool_dropped(caplog):
    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "tool", "tool_call_id": "oops", "content": "{}"},
    ]
    with caplog.at_level(logging.WARNING):
        out = preflight_validate_messages(msgs)
    assert out == [msgs[0]]
    rec = caplog.records[0]
    data = json.loads(rec.message)
    assert data["tool_call_id"] == "oops"
    assert data["reason"] == "missing parent assistant"
    assert data["excerpt"][0] == {"index": 0, "role": "user"}


def test_mixed_valid_invalid_tools(caplog):
    msgs = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "a1", "type": "function", "function": {"name": "x", "arguments": "{}"}}
            ],
        },
        {"role": "tool", "tool_call_id": "a1", "content": "ok"},
        {"role": "tool", "tool_call_id": "missing", "content": "bad"},
    ]
    with caplog.at_level(logging.WARNING):
        out = preflight_validate_messages(msgs)
    assert out == msgs[:2]
    assert len(caplog.records) == 1
    data = json.loads(caplog.records[0].message)
    assert data["tool_call_id"] == "missing"
    assert data["reason"] == "unknown tool_call_id"
