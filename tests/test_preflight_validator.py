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
    assert rec.message == "drop_orphan_tool"
    payload = rec.__dict__["payload"]
    assert payload["tool_call_id"] == "oops"
    assert payload["reason"] == "no_adjacent_parent"
    assert payload["idx"] == 1


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
    rec = caplog.records[0]
    assert rec.message == "drop_orphan_tool"
    payload = rec.__dict__["payload"]
    assert payload["tool_call_id"] == "missing"
    assert payload["reason"] == "no_adjacent_parent"
    assert payload["idx"] == 2


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
    payload = caplog.records[0].__dict__["payload"]
    assert payload["reason"] == "no_adjacent_parent"

    slice_msgs = extract_tool_exchange_slice(msgs)
    assert slice_msgs is None


def test_tool_exchange_slice_minimal():
    msgs = [
        {"role": "system", "content": "s1"},
        {"role": "user", "content": "u0"},
        {"role": "system", "content": "s2"},
        {"role": "user", "content": "u"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "a1", "type": "function", "function": {"name": "x", "arguments": "{}"}}
            ],
        },
        {"role": "tool", "tool_call_id": "a1", "content": "ok"},
        {"role": "tool", "tool_call_id": "a1", "content": "more"},
    ]

    slice_msgs = extract_tool_exchange_slice(msgs)
    assert slice_msgs == [
        {"role": "system", "content": "s2"},
        {"role": "user", "content": "u"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "a1", "type": "function", "function": {"name": "x", "arguments": "{}"}}
            ],
        },
        {"role": "tool", "tool_call_id": "a1", "content": "ok"},
        {"role": "tool", "tool_call_id": "a1", "content": "more"},
    ]
