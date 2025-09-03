"""Test safe_invoke integration with mixed input types."""
import pytest
from unittest.mock import Mock, AsyncMock
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from orchestrator.llm.safe_invoke import _invoke_threaded


@pytest.fixture(autouse=True)
def patch_graph():
    """Override global fixture from conftest; not needed here."""
    yield


@pytest.mark.asyncio
async def test_invoke_threaded_with_mixed_inputs():
    """Test _invoke_threaded handles mixed dict/BaseMessage inputs correctly."""
    # Create a mock LLM that returns a simple response
    mock_response = AIMessage(content="Response")
    mock_llm = Mock()
    mock_llm.invoke.return_value = mock_response
    
    # Mixed input: dict + BaseMessage + dict
    mixed_messages = [
        {"role": "system", "content": "You are helpful"},  # dict
        HumanMessage(content="Hello"),  # BaseMessage
        {
            "role": "assistant", 
            "content": "I'll help",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function", 
                    "function": {
                        "name": "search", 
                        "arguments": '{"query": "test"}'
                    }
                }
            ]
        },  # dict with OpenAI-style tool calls
        ToolMessage(content="Found results", tool_call_id="call_1"),  # BaseMessage
    ]
    
    # Should process successfully without any validation errors
    result = await _invoke_threaded(mock_llm, mixed_messages)
    
    # Verify the mock was called and returned correctly
    assert result == mock_response
    assert mock_llm.invoke.called
    
    # Verify the processed messages were properly converted to LangChain format
    call_args = mock_llm.invoke.call_args[0][0]  # First positional arg
    assert len(call_args) == 4
    assert isinstance(call_args[0], SystemMessage)
    assert isinstance(call_args[1], HumanMessage) 
    assert isinstance(call_args[2], AIMessage)
    assert isinstance(call_args[3], ToolMessage)
    
    # Verify OpenAI-style tool call was normalized to LC format
    ai_msg = call_args[2]
    assert len(ai_msg.tool_calls) == 1
    assert ai_msg.tool_calls[0]["name"] == "search"
    assert ai_msg.tool_calls[0]["args"] == {"query": "test"}


@pytest.mark.asyncio
async def test_invoke_threaded_with_pure_basemessages():
    """Test _invoke_threaded with pure BaseMessage input (no conversion needed)."""
    mock_response = AIMessage(content="Response")
    mock_llm = Mock()
    mock_llm.invoke.return_value = mock_response
    
    # Create AI message with tool calls that need normalization
    ai_msg = AIMessage(content="I'll search")
    ai_msg.additional_kwargs = {
        "tool_calls": [
            {
                "id": "call_search",
                "type": "function",
                "function": {
                    "name": "web_search", 
                    "arguments": '{"q": "python"}'
                }
            }
        ]
    }
    
    basemessage_input = [
        SystemMessage(content="System prompt"),
        HumanMessage(content="User question"),
        ai_msg,
        ToolMessage(content="Search results", tool_call_id="call_search")
    ]
    
    result = await _invoke_threaded(mock_llm, basemessage_input)
    
    assert result == mock_response
    assert mock_llm.invoke.called
    
    # Verify AI message tool calls were normalized
    call_args = mock_llm.invoke.call_args[0][0]
    ai_processed = call_args[2]
    assert len(ai_processed.tool_calls) == 1
    assert ai_processed.tool_calls[0]["name"] == "web_search"
    assert ai_processed.tool_calls[0]["args"] == {"q": "python"}


@pytest.mark.asyncio
async def test_invoke_threaded_orphan_tool_filtering():
    """Test that orphan tools are properly filtered in the pipeline."""
    mock_response = AIMessage(content="Response")
    mock_llm = Mock()
    mock_llm.invoke.return_value = mock_response
    
    # Input with orphan tool message
    messages_with_orphan = [
        {"role": "user", "content": "Hello"},
        {"role": "tool", "content": "orphan result", "tool_call_id": "orphan_call"},
        {"role": "assistant", "content": "I can help"}
    ]
    
    result = await _invoke_threaded(mock_llm, messages_with_orphan)
    
    assert result == mock_response
    
    # Verify orphan tool was filtered out
    call_args = mock_llm.invoke.call_args[0][0]
    assert len(call_args) == 2  # Only user and assistant, orphan tool filtered
    assert isinstance(call_args[0], HumanMessage)
    assert isinstance(call_args[1], AIMessage)