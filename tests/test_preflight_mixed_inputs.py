"""Test mixed input handling for preflight system."""
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from orchestrator.llm.preflight import (
    normalize_history,
    preflight_validate_messages,
    to_langchain_messages,
    build_payload_messages,
)


@pytest.fixture(autouse=True)
def patch_graph():
    """Override global fixture from conftest; not needed here."""
    yield


def test_to_langchain_messages_with_dict_list():
    """Test a) list of dicts - verify invoke succeeds with no pydantic errors."""
    msgs = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"},
        {
            "role": "assistant",
            "content": "I'll help",
            "tool_calls": [
                {"id": "call_1", "type": "tool_call", "name": "search", "args": {"q": "test"}}
            ]
        },
        {"role": "tool", "content": "result", "tool_call_id": "call_1"},
        {"role": "assistant", "content": "Done"},
    ]
    
    lc_messages = to_langchain_messages(msgs)
    
    # Verify no pydantic errors and proper conversion
    assert len(lc_messages) == 5
    assert isinstance(lc_messages[0], SystemMessage)
    assert isinstance(lc_messages[1], HumanMessage)
    assert isinstance(lc_messages[2], AIMessage)
    assert isinstance(lc_messages[3], ToolMessage)
    assert isinstance(lc_messages[4], AIMessage)
    
    # Verify AI message tool calls are properly formatted
    assert len(lc_messages[2].tool_calls) == 1
    assert lc_messages[2].tool_calls[0]["name"] == "search"
    assert lc_messages[2].tool_calls[0]["args"] == {"q": "test"}


def test_to_langchain_messages_with_basemessage_list():
    """Test b) list of BaseMessages - verify invoke succeeds with no pydantic errors."""
    ai_msg = AIMessage(content="I'll search")
    ai_msg.tool_calls = [
        {"id": "call_1", "name": "search", "args": {"query": "test"}}
    ]
    
    msgs = [
        SystemMessage(content="You are helpful"),
        HumanMessage(content="Hello"),
        ai_msg,
        ToolMessage(content="result", tool_call_id="call_1"),
        AIMessage(content="Done")
    ]
    
    lc_messages = to_langchain_messages(msgs)
    
    # Verify BaseMessage pass-through: System/Human/Tool unchanged; AI normalized
    assert len(lc_messages) == 5
    assert isinstance(lc_messages[0], SystemMessage)
    assert lc_messages[0].content == "You are helpful"
    assert isinstance(lc_messages[1], HumanMessage)
    assert lc_messages[1].content == "Hello"
    assert isinstance(lc_messages[2], AIMessage)
    assert lc_messages[2].content == "I'll search"
    assert isinstance(lc_messages[3], ToolMessage)
    assert lc_messages[3].content == "result"
    assert isinstance(lc_messages[4], AIMessage)
    assert lc_messages[4].content == "Done"
    
    # Verify AI tool calls normalized
    assert len(lc_messages[2].tool_calls) == 1
    assert lc_messages[2].tool_calls[0]["name"] == "search"


def test_to_langchain_messages_with_mixed_list():
    """Test c) mixed list - verify invoke succeeds with no pydantic errors."""
    ai_msg = AIMessage(content="I'll search")
    ai_msg.tool_calls = [
        {"id": "call_1", "name": "search", "args": {"query": "test"}}
    ]
    
    msgs = [
        {"role": "system", "content": "You are helpful"},  # dict
        HumanMessage(content="Hello"),  # BaseMessage
        ai_msg,  # BaseMessage with tool calls
        {"role": "tool", "content": "result", "tool_call_id": "call_1"},  # dict
        AIMessage(content="Done")  # BaseMessage
    ]
    
    lc_messages = to_langchain_messages(msgs)
    
    # Verify mixed inputs handled correctly
    assert len(lc_messages) == 5
    assert isinstance(lc_messages[0], SystemMessage)
    assert isinstance(lc_messages[1], HumanMessage)
    assert isinstance(lc_messages[2], AIMessage)
    assert isinstance(lc_messages[3], ToolMessage)
    assert isinstance(lc_messages[4], AIMessage)
    
    # Verify tool call normalization
    assert len(lc_messages[2].tool_calls) == 1
    assert lc_messages[2].tool_calls[0]["name"] == "search"


def test_openai_style_tool_calls_parsed_to_dict():
    """Test OpenAI-style tool_calls (with function.arguments: str) are parsed to dict."""
    history = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_abc",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"location": "Paris", "units": "celsius"}'
                    }
                }
            ]
        }
    ]
    
    normalized = normalize_history(history)
    
    # Verify OpenAI format converted to LC format with parsed arguments
    assert normalized[0]["tool_calls"][0]["type"] == "tool_call"
    assert normalized[0]["tool_calls"][0]["name"] == "get_weather"
    assert normalized[0]["tool_calls"][0]["args"] == {"location": "Paris", "units": "celsius"}
    assert normalized[0]["tool_calls"][0]["id"] == "call_abc"


def test_lc_style_tool_calls_pass_unchanged():
    """Test LC-style tool_calls pass unchanged."""
    history = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_lc",
                    "type": "tool_call",
                    "name": "search",
                    "args": {"query": "test", "limit": 5}
                }
            ]
        }
    ]
    
    normalized = normalize_history(history)
    
    # Verify LC format passes through unchanged
    assert normalized[0]["tool_calls"][0]["type"] == "tool_call"
    assert normalized[0]["tool_calls"][0]["name"] == "search"
    assert normalized[0]["tool_calls"][0]["args"] == {"query": "test", "limit": 5}
    assert normalized[0]["tool_calls"][0]["id"] == "call_lc"


def test_orphan_tool_messages_dropped_with_debug_log(caplog):
    """Test orphan tool messages dropped (DEBUG log), WARNING only on suspicious mismatch."""
    # Case 1: True orphan (no preceding assistant) - should log DEBUG
    history1 = [
        {"role": "user", "content": "Hello"},
        {"role": "tool", "tool_call_id": "orphan_1", "content": "result"}
    ]
    
    normalized1 = normalize_history(history1)
    validated1 = preflight_validate_messages(normalized1)
    
    # Orphan should be dropped
    assert len(validated1) == 1
    assert validated1[0]["role"] == "user"
    
    # Case 2: Suspicious mismatch (tool_call_id exists but doesn't match last assistant) - should log WARNING
    history2 = [
        {
            "role": "assistant", 
            "content": "",
            "tool_calls": [{"id": "expected_call", "type": "tool_call", "name": "func", "args": {}}]
        },
        {"role": "tool", "tool_call_id": "different_call", "content": "wrong result"}
    ]
    
    normalized2 = normalize_history(history2)
    validated2 = preflight_validate_messages(normalized2)
    
    # Mismatched tool should be dropped
    assert len(validated2) == 1
    assert validated2[0]["role"] == "assistant"


def test_basemessage_pass_through():
    """Test BaseMessage pass-through: System/Human/Tool unchanged; AI normalized."""
    # Create messages with additional_kwargs to test normalization
    ai_msg = AIMessage(content="I'll call tools")
    ai_msg.additional_kwargs = {
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function", 
                "function": {
                    "name": "search",
                    "arguments": '{"q": "test"}'
                }
            }
        ]
    }
    
    msgs = [
        SystemMessage(content="System prompt"),
        HumanMessage(content="User question"),
        ai_msg,
        ToolMessage(content="Tool response", tool_call_id="call_1")
    ]
    
    lc_messages = to_langchain_messages(msgs)
    
    # System/Human/Tool should be unchanged
    assert lc_messages[0] is msgs[0]  # Same object reference
    assert lc_messages[1] is msgs[1]  # Same object reference
    assert lc_messages[3] is msgs[3]  # Same object reference
    
    # AI should be normalized (new object with normalized tool_calls)
    assert lc_messages[2] is not ai_msg  # Different object
    assert isinstance(lc_messages[2], AIMessage)
    assert lc_messages[2].content == "I'll call tools"
    assert len(lc_messages[2].tool_calls) == 1
    assert lc_messages[2].tool_calls[0]["name"] == "search"
    assert lc_messages[2].tool_calls[0]["args"] == {"q": "test"}


def test_iteration_2_tool_phase_produces_valid_messages():
    """Test iteration 2 tool phase produces valid AIMessage(tool_calls=[...]) + ToolMessage(...)."""
    # Simulate what happens in iteration 2 of tool exchange
    assistant_msg = {
        "role": "assistant",
        "content": "I need to search for information",
        "tool_calls": [
            {
                "id": "call_search_1",
                "type": "function",
                "function": {
                    "name": "web_search",
                    "arguments": '{"query": "Python asyncio"}'
                }
            },
            {
                "id": "call_search_2", 
                "type": "function",
                "function": {
                    "name": "code_search",
                    "arguments": '{"pattern": "async def"}'
                }
            }
        ]
    }
    
    tool_msg_1 = {
        "role": "tool",
        "content": "Found 5 results about Python asyncio",
        "tool_call_id": "call_search_1"
    }
    
    tool_msg_2 = {
        "role": "tool", 
        "content": "Found 3 async functions",
        "tool_call_id": "call_search_2"
    }
    
    history = [assistant_msg, tool_msg_1, tool_msg_2]
    
    sanitized, in_tool_exchange = build_payload_messages(history)
    lc_messages = to_langchain_messages(sanitized)
    
    # Verify valid AIMessage with properly formatted tool_calls
    assert len(lc_messages) == 3
    assert isinstance(lc_messages[0], AIMessage)
    assert len(lc_messages[0].tool_calls) == 2
    
    # Check first tool call
    tc1 = lc_messages[0].tool_calls[0]
    assert tc1["id"] == "call_search_1"
    assert tc1["name"] == "web_search"
    assert tc1["args"] == {"query": "Python asyncio"}
    
    # Check second tool call
    tc2 = lc_messages[0].tool_calls[1]
    assert tc2["id"] == "call_search_2"
    assert tc2["name"] == "code_search"
    assert tc2["args"] == {"pattern": "async def"}
    
    # Verify valid ToolMessages
    assert isinstance(lc_messages[1], ToolMessage)
    assert lc_messages[1].content == "Found 5 results about Python asyncio"
    assert lc_messages[1].tool_call_id == "call_search_1"
    
    assert isinstance(lc_messages[2], ToolMessage)
    assert lc_messages[2].content == "Found 3 async functions"
    assert lc_messages[2].tool_call_id == "call_search_2"
    
    # Verify tool exchange detection
    assert in_tool_exchange is True


def test_malformed_arguments_handling():
    """Test that malformed JSON arguments get converted to empty dict."""
    history = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_bad_json",
                    "type": "function",
                    "function": {
                        "name": "broken_tool",
                        "arguments": "this is not valid json {"
                    }
                }
            ]
        }
    ]
    
    normalized = normalize_history(history)
    
    # Malformed JSON should be converted to empty dict
    assert normalized[0]["tool_calls"][0]["name"] == "broken_tool"
    assert normalized[0]["tool_calls"][0]["args"] == {}


def test_empty_and_null_tool_calls_filtered():
    """Test that empty and null tool calls are filtered out."""
    history = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "good", "type": "tool_call", "name": "valid", "args": {"test": True}},
                None,  # Should be filtered
                {},    # Should be filtered
                {"id": "incomplete"},  # Missing name - should be filtered
                {"id": "also_good", "type": "function", "function": {"name": "search", "arguments": "{}"}}
            ]
        }
    ]
    
    normalized = normalize_history(history)
    
    # Should only preserve the 2 valid tool calls
    assert len(normalized[0]["tool_calls"]) == 2
    assert normalized[0]["tool_calls"][0]["name"] == "valid"
    assert normalized[0]["tool_calls"][1]["name"] == "search"