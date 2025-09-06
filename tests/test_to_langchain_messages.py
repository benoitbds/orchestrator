import pytest
from orchestrator.llm.preflight import to_langchain_messages
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage


@pytest.fixture(autouse=True)
def patch_graph():
    """Override heavy fixture from tests.conftest."""
    yield


def test_to_langchain_messages_basic_mapping():
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
        {
            "role": "assistant",
            "content": "ok",
            "tool_calls": [{"id": "1", "name": "foo", "args": {"x": 1}}],
        },
        {"role": "tool", "content": "result", "tool_call_id": "1"},
    ]
    lc = to_langchain_messages(msgs)
    assert isinstance(lc[0], SystemMessage)
    assert lc[0].content == "sys"
    assert isinstance(lc[1], HumanMessage)
    assert lc[1].content == "hi"
    assert isinstance(lc[2], AIMessage)
    assert lc[2].tool_calls[0]["name"] == "foo"
    assert isinstance(lc[3], ToolMessage)
    assert lc[3].tool_call_id == "1"


def test_to_langchain_messages_unknown_role_defaults_to_human():
    msgs = [{"role": "other", "content": "x"}]
    lc = to_langchain_messages(msgs)
    assert isinstance(lc[0], HumanMessage)


def test_to_langchain_messages_missing_content_empty_string():
    msgs = [{"role": "system"}]
    lc = to_langchain_messages(msgs)
    assert lc[0].content == ""


def test_to_langchain_messages_accepts_base_messages():
    msgs = [SystemMessage(content="sys"), {"role": "user", "content": "hi"}]
    lc = to_langchain_messages(msgs)
    assert isinstance(lc[0], SystemMessage)
    assert isinstance(lc[1], HumanMessage)


def test_to_langchain_messages_normalizes_openai_tool_calls():
    ai = AIMessage(
        content="ok",
        additional_kwargs={
            "tool_calls": [
                {"id": "1", "function": {"name": "foo", "arguments": "{\"x\":1}"}}
            ]
        },
    )
    lc = to_langchain_messages([ai])
    assert lc[0].tool_calls == [
        {"id": "1", "type": "tool_call", "name": "foo", "args": {"x": 1}}
    ]


class DummyLLM:
    def __init__(self):
        self.received = None

    def invoke(self, messages):
        self.received = messages
        return "ok"


@pytest.mark.asyncio
async def test_invoke_threaded_converts_dicts_to_messages():
    from orchestrator.llm.safe_invoke import _invoke_threaded

    llm = DummyLLM()
    result = await _invoke_threaded(llm, [{"role": "user", "content": "hi"}])
    assert result == "ok"
    assert isinstance(llm.received[0], HumanMessage)
