import json
import logging
import pytest
from orchestrator.llm.preflight import (
    preflight_validate_messages,
    extract_tool_exchange_slice,
)


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
    assert data["event"] == "drop_orphan_tool"
    assert data["tool_call_id"] == "oops"
    assert data["reason"] == "missing parent assistant"
    assert data["idx"] == 1


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
    assert data["event"] == "drop_orphan_tool"
    assert data["tool_call_id"] == "missing"
    assert data["reason"] == "unknown tool_call_id"
    assert data["idx"] == 2


def test_non_adjacent_tool_slice(caplog):
    msgs = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u1"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "a1", "type": "function", "function": {"name": "x", "arguments": "{}"}}
            ],
        },
        {"role": "user", "content": "noise"},
        {"role": "tool", "tool_call_id": "a1", "content": "{}"},
    ]

    with caplog.at_level(logging.WARNING):
        full = preflight_validate_messages(msgs)
    # tool dropped because it's not adjacent
    assert full == msgs[:-1]
    data = json.loads(caplog.records[0].message)
    assert data["reason"] == "missing parent assistant"

    slice_msgs = extract_tool_exchange_slice(msgs)
    assert slice_msgs == [msgs[0], msgs[1], msgs[2], msgs[4]]
    out = preflight_validate_messages(slice_msgs)
    assert out == slice_msgs
