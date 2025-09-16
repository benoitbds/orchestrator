import logging

import pytest

import orchestrator.agent_response as agent_response
import orchestrator.conversation_memory as conversation_memory_module
from orchestrator.agent_response import generate_agent_response
from orchestrator.conversation_memory import ConversationMemory


@pytest.fixture
def memory(monkeypatch):
    monkeypatch.setattr(
        conversation_memory_module.ConversationMemory,
        "_maybe_summarize",
        lambda self: None,
    )
    return ConversationMemory()


def test_generate_agent_response_builds_prompt_with_context(monkeypatch, memory):
    calls = []

    def fake_summarize(self):
        calls.append(True)
        return False

    monkeypatch.setattr(
        conversation_memory_module.ConversationMemory,
        "summarize_conversation",
        fake_summarize,
    )

    memory.update_summary("Earlier context")
    memory.add_message("assistant", "Previous reply")

    monkeypatch.setattr(
        agent_response,
        "retrieve_external_info",
        lambda query: "External details" if query == "What is AI?" else "",
    )

    captured = {}

    class DummyChatCompletion:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            return {
                "choices": [
                    {"message": {"content": "AI stands for Artificial Intelligence."}}
                ]
            }

    monkeypatch.setattr(agent_response.openai, "ChatCompletion", DummyChatCompletion)

    reply = generate_agent_response(
        "What is AI?",
        memory,
        system_prompt="System prompt",
        model="test-model",
        recent_message_count=5,
    )

    assert reply == "AI stands for Artificial Intelligence."
    assert memory.messages[-1] == {
        "role": "assistant",
        "content": "AI stands for Artificial Intelligence.",
    }
    assert calls == [True]

    assert captured["model"] == "test-model"
    assert captured["messages"][0] == {
        "role": "system",
        "content": "System prompt",
    }
    assert captured["messages"][1] == {
        "role": "system",
        "content": "Relevant information: External details",
    }

    history = captured["messages"][2:-1]
    assert history[0]["role"] == "system"
    assert "Summary of previous conversation" in history[0]["content"]
    assert history[1] == {"role": "assistant", "content": "Previous reply"}

    assert captured["messages"][-1] == {"role": "user", "content": "What is AI?"}


def test_generate_agent_response_returns_fallback_on_openai_error(monkeypatch, memory):
    monkeypatch.setattr(
        agent_response,
        "retrieve_external_info",
        lambda _: "",
    )

    class DummyChatCompletion:
        @staticmethod
        def create(**kwargs):
            raise RuntimeError("OpenAI unavailable")

    monkeypatch.setattr(agent_response.openai, "ChatCompletion", DummyChatCompletion)

    reply = generate_agent_response(
        "Tell me a joke",
        memory,
        system_prompt="System prompt",
    )

    assert reply == agent_response.FALLBACK_ASSISTANT_RESPONSE
    assert memory.messages[-1] == {
        "role": "assistant",
        "content": agent_response.FALLBACK_ASSISTANT_RESPONSE,
    }


@pytest.mark.parametrize("user_input", ["", "   ", 123])
def test_generate_agent_response_validates_input(user_input, memory):
    with pytest.raises((TypeError, ValueError)):
        generate_agent_response(user_input, memory, system_prompt="System prompt")


def test_generate_agent_response_handles_external_info_failure(
    monkeypatch, memory, caplog
):
    def broken_lookup(_):
        raise RuntimeError("lookup failed")

    monkeypatch.setattr(agent_response, "retrieve_external_info", broken_lookup)

    captured = {}

    class DummyChatCompletion:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            return {
                "choices": [
                    {"message": {"content": "Here is your answer."}}
                ]
            }

    monkeypatch.setattr(agent_response.openai, "ChatCompletion", DummyChatCompletion)

    with caplog.at_level(logging.WARNING):
        reply = generate_agent_response(
            "Need info",
            memory,
            system_prompt="System prompt",
        )

    assert reply == "Here is your answer."
    assert any(
        "Failed to retrieve external information" in record.message
        for record in caplog.records
    )
    assert all(
        msg["role"] != "system" or not msg["content"].startswith("Relevant information")
        for msg in captured["messages"][1:-1]
    )
