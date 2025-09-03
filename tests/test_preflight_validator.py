import logging
import pytest
from orchestrator.llm.preflight import (
    normalize_history,
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
    normalized = normalize_history(msgs)
    out = preflight_validate_messages(normalized)
    assert out == [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "a1", "type": "tool_call", "name": "x", "args": {}}
            ],
        },
        {"role": "tool", "tool_call_id": "a1", "content": "{}"},
    ]
    assert out is not msgs


def test_invalid_tool_dropped(caplog):
    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "tool", "tool_call_id": "oops", "content": "{}"},
    ]
    normalized = normalize_history(msgs)
    with caplog.at_level(logging.DEBUG):
        out = preflight_validate_messages(normalized)
    assert out == [msgs[0]]
    rec = caplog.records[0]
    assert rec.message == "drop_orphan_tool"
    assert rec.levelno == logging.DEBUG
    payload = rec.__dict__["payload"]
    assert payload["tool_call_id"] == "oops"
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
    normalized = normalize_history(msgs)
    with caplog.at_level(logging.WARNING):
        out = preflight_validate_messages(normalized)
    assert out == [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "a1", "type": "tool_call", "name": "x", "args": {}}
            ],
        },
        {"role": "tool", "tool_call_id": "a1", "content": "ok"},
    ]
    assert len(caplog.records) == 1
    rec = caplog.records[0]
    assert rec.message == "drop_orphan_tool"
    assert rec.levelno == logging.WARNING
    payload = rec.__dict__["payload"]
    assert payload["tool_call_id"] == "missing"
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

    normalized = normalize_history(msgs)
    with caplog.at_level(logging.DEBUG):
        full = preflight_validate_messages(normalized)
    assert full == [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u1"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "a1", "type": "tool_call", "name": "x", "args": {}}
            ],
        },
        {"role": "user", "content": "noise"},
    ]
    rec = caplog.records[0]
    assert rec.levelno == logging.DEBUG
    payload = rec.__dict__["payload"]
    assert payload["tool_call_id"] == "a1"

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
                {"id": "a1", "type": "tool_call", "name": "x", "args": {}}
            ],
        },
        {"role": "tool", "tool_call_id": "a1", "content": "ok"},
        {"role": "tool", "tool_call_id": "a1", "content": "more"},
    ]
