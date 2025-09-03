import asyncio
import json
import logging
import pytest
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, ChatMessage

from orchestrator.llm.preflight import (
    normalize_history,
    preflight_validate_messages,
    to_langchain_messages,
    extract_tool_exchange_slice,
)


@pytest.fixture(autouse=True)
def patch_graph():
    """Override global fixture from conftest; not needed here."""
    yield


def test_to_langchain_messages_conversion():
    """Test conversion from sanitized dicts to BaseMessages."""
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
    
    assert len(lc_messages) == 5
    assert isinstance(lc_messages[0], SystemMessage)
    assert lc_messages[0].content == "You are helpful"
    
    assert isinstance(lc_messages[1], HumanMessage)
    assert lc_messages[1].content == "Hello"
    
    assert isinstance(lc_messages[2], AIMessage)
    assert lc_messages[2].content == "I'll help"
    assert len(lc_messages[2].tool_calls) == 1
    assert lc_messages[2].tool_calls[0]["name"] == "search"
    
    assert isinstance(lc_messages[3], ToolMessage)
    assert lc_messages[3].content == "result"
    assert lc_messages[3].tool_call_id == "call_1"
    
    assert isinstance(lc_messages[4], AIMessage)
    assert lc_messages[4].content == "Done"
    assert len(getattr(lc_messages[4], 'tool_calls', [])) == 0


def test_to_langchain_messages_custom_role():
    """Test handling of custom roles."""
    msgs = [{"role": "custom", "content": "custom message"}]
    lc_messages = to_langchain_messages(msgs)
    
    assert len(lc_messages) == 1
    assert isinstance(lc_messages[0], ChatMessage)
    assert lc_messages[0].role == "custom"
    assert lc_messages[0].content == "custom message"


def test_openai_shaped_tool_calls_normalization():
    """Test OpenAI function format gets coerced to LC shape."""
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
                        "arguments": '{"location": "Paris"}'
                    }
                }
            ]
        },
        {"role": "tool", "tool_call_id": "call_abc", "content": "Sunny, 22°C"}
    ]
    
    normalized = normalize_history(history)
    sanitized = preflight_validate_messages(normalized)
    
    # Check that OpenAI format was converted to LC format
    assert sanitized[0]["tool_calls"][0]["type"] == "tool_call"
    assert sanitized[0]["tool_calls"][0]["name"] == "get_weather"
    assert sanitized[0]["tool_calls"][0]["args"] == {"location": "Paris"}
    assert sanitized[0]["tool_calls"][0]["id"] == "call_abc"


def test_mixed_dict_and_lc_input():
    """Test handling mixed input types (dict and LangChain objects)."""
    ai_msg = AIMessage(content="I'll search")
    ai_msg.tool_calls = [
        {"id": "call_1", "name": "search", "args": {"query": "test"}}
    ]
    
    history = [
        {"role": "user", "content": "Search for something"},
        ai_msg,
        ToolMessage(content="Found it", tool_call_id="call_1")
    ]
    
    normalized = normalize_history(history)
    sanitized = preflight_validate_messages(normalized)
    
    assert len(sanitized) == 3
    assert sanitized[0]["role"] == "user"
    assert sanitized[1]["role"] == "assistant"
    assert sanitized[1]["tool_calls"][0]["name"] == "search"
    assert sanitized[2]["role"] == "tool"
    assert sanitized[2]["tool_call_id"] == "call_1"


def test_concurrent_normalization_safety():
    """Test that concurrent normalize_history calls don't interfere."""
    async def normalize_task(task_id: int):
        history = [
            {"role": "user", "content": f"Hello from task {task_id}"},
            {
                "role": "assistant",
                "content": f"Response {task_id}",
                "tool_calls": [
                    {
                        "id": f"call_{task_id}",
                        "type": "function",
                        "function": {
                            "name": "task_function",
                            "arguments": json.dumps({"task_id": task_id})
                        }
                    }
                ]
            },
            {"role": "tool", "tool_call_id": f"call_{task_id}", "content": f"Result {task_id}"}
        ]
        
        # Simulate some async work
        await asyncio.sleep(0.01)
        
        normalized = normalize_history(history)
        sanitized = preflight_validate_messages(normalized)
        
        # Verify task-specific data is preserved correctly
        assert sanitized[0]["content"] == f"Hello from task {task_id}"
        assert sanitized[1]["content"] == f"Response {task_id}"
        assert sanitized[1]["tool_calls"][0]["id"] == f"call_{task_id}"
        assert sanitized[1]["tool_calls"][0]["args"]["task_id"] == task_id
        assert sanitized[2]["content"] == f"Result {task_id}"
        
        return task_id
    
    async def run_concurrent_test():
        tasks = [normalize_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        assert results == list(range(10))
    
    # Run the concurrent test
    asyncio.run(run_concurrent_test())


def test_orphan_tool_warning_vs_debug_logging(caplog):
    """Test that orphan tools log at WARNING when part of expected tool calls."""
    # First case: orphan tool with no prior assistant - should log DEBUG
    history1 = [
        {"role": "user", "content": "Hello"},
        {"role": "tool", "tool_call_id": "orphan_1", "content": "result"}
    ]
    
    normalized1 = normalize_history(history1)
    with caplog.at_level(logging.DEBUG):
        preflight_validate_messages(normalized1)
    
    debug_record = next((r for r in caplog.records if r.message == "drop_orphan_tool"), None)
    assert debug_record is not None
    assert debug_record.levelno == logging.DEBUG
    
    caplog.clear()
    
    # Second case: tool with ID that doesn't match the last assistant's calls - should log WARNING
    history2 = [
        {
            "role": "assistant", 
            "content": "",
            "tool_calls": [{"id": "expected_call", "type": "tool_call", "name": "func", "args": {}}]
        },
        {"role": "tool", "tool_call_id": "different_call", "content": "wrong result"}
    ]
    
    normalized2 = normalize_history(history2)
    with caplog.at_level(logging.DEBUG):
        preflight_validate_messages(normalized2)
    
    warning_record = next((r for r in caplog.records if r.message == "drop_orphan_tool"), None)
    assert warning_record is not None
    assert warning_record.levelno == logging.WARNING


def test_malformed_tool_call_handling():
    """Test handling of malformed tool call structures."""
    history = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                # Valid call
                {"id": "good", "type": "function", "function": {"name": "valid", "arguments": "{}"}},
                # Missing name
                {"id": "bad1", "type": "function", "function": {"arguments": "{}"}},
                # Invalid arguments (gets coerced to empty dict)
                {"id": "bad2", "type": "function", "function": {"name": "invalid", "arguments": "not json"}},
                # Null/empty
                None,
                {},
                # Direct LC format (should pass through)
                {"id": "lc", "type": "tool_call", "name": "langchain", "args": {"test": True}}
            ]
        }
    ]
    
    normalized = normalize_history(history)
    
    # Should preserve valid tool calls (invalid JSON args get converted to empty dict)
    assert len(normalized[0]["tool_calls"]) == 3
    assert normalized[0]["tool_calls"][0]["name"] == "valid"
    assert normalized[0]["tool_calls"][0]["args"] == {}
    assert normalized[0]["tool_calls"][1]["name"] == "invalid"
    assert normalized[0]["tool_calls"][1]["args"] == {}  # invalid JSON becomes empty dict
    assert normalized[0]["tool_calls"][2]["name"] == "langchain"
    assert normalized[0]["tool_calls"][2]["args"] == {"test": True}


def test_empty_history_handling():
    """Test handling of empty or None inputs."""
    assert normalize_history([]) == []
    assert preflight_validate_messages([]) == []
    assert to_langchain_messages([]) == []
    assert extract_tool_exchange_slice([]) is None