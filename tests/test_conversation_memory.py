import logging

import pytest

import orchestrator.conversation_memory as conversation_memory_module
from orchestrator.conversation_memory import ConversationMemory


@pytest.fixture
def memory():
    return ConversationMemory()


class TestAddMessage:
    def test_adds_message_to_history(self, memory):
        memory.add_message("user", "Hello")

        assert memory.messages == [{"role": "user", "content": "Hello"}]

    @pytest.mark.parametrize("role", ["", "   ", 123])
    def test_rejects_invalid_role(self, memory, role):
        with pytest.raises(ValueError):
            memory.add_message(role, "content")

    def test_rejects_non_string_content(self, memory):
        with pytest.raises(ValueError):
            memory.add_message("user", 42)


class TestUpdateSummary:
    def test_updates_summary(self, memory):
        memory.update_summary("Past details")

        assert memory.summary == "Past details"

    def test_update_summary_strips_whitespace(self, memory):
        memory.update_summary("  trimmed  ")

        assert memory.summary == "trimmed"


class TestGetRecentMessages:
    def test_returns_recent_messages_up_to_n(self, memory):
        for index in range(6):
            memory.add_message("user", f"msg {index}")

        recent = memory.get_recent_messages(3)

        assert [m["content"] for m in recent] == ["msg 3", "msg 4", "msg 5"]

    def test_includes_summary_when_available(self, memory):
        memory.add_message("user", "Hi")
        memory.update_summary("Earlier context")

        result = memory.get_recent_messages(1)

        assert result[0] == {
            "role": "system",
            "content": "Summary of previous conversation: Earlier context",
        }
        assert result[1] == {"role": "user", "content": "Hi"}

    def test_rejects_non_positive_n(self, memory):
        with pytest.raises(ValueError):
            memory.get_recent_messages(0)


class TestSummarizeConversation:
    def test_auto_summarize_trims_history_and_updates_summary(
        self, memory, monkeypatch
    ):
        captured_kwargs = {}

        class DummyChatCompletion:
            @staticmethod
            def create(**kwargs):
                captured_kwargs.update(kwargs)
                return {
                    "choices": [
                        {"message": {"content": "Updated summary of conversation"}}
                    ]
                }

        monkeypatch.setattr(
            conversation_memory_module.openai,
            "ChatCompletion",
            DummyChatCompletion,
        )

        for index in range(ConversationMemory.SUMMARIZE_THRESHOLD + 1):
            role = "user" if index % 2 == 0 else "assistant"
            memory.add_message(role, f"message {index}")

        assert memory.summary == "Updated summary of conversation"
        assert len(memory.messages) == ConversationMemory.SUMMARY_RECENT_MESSAGES
        assert captured_kwargs["model"] == ConversationMemory.SUMMARY_MODEL
        assert "Existing summary" in captured_kwargs["messages"][1]["content"]

    def test_manual_summarize_returns_false_when_below_threshold(
        self, memory, monkeypatch
    ):
        class DummyChatCompletion:
            @staticmethod
            def create(**_):
                raise AssertionError("ChatCompletion should not be invoked")

        monkeypatch.setattr(
            conversation_memory_module.openai,
            "ChatCompletion",
            DummyChatCompletion,
        )

        for index in range(ConversationMemory.SUMMARIZE_THRESHOLD):
            memory.add_message("user", f"short {index}")

        assert memory.summarize_conversation() is False

    def test_add_message_logs_warning_when_summary_fails(
        self, memory, monkeypatch, caplog
    ):
        class DummyChatCompletion:
            @staticmethod
            def create(**_):
                raise RuntimeError("boom")

        monkeypatch.setattr(
            conversation_memory_module.openai,
            "ChatCompletion",
            DummyChatCompletion,
        )

        with caplog.at_level(logging.WARNING):
            for index in range(ConversationMemory.SUMMARIZE_THRESHOLD):
                memory.add_message("user", f"message {index}")

            memory.add_message("assistant", "trigger summary failure")

        assert "Skipping conversation summarization" in caplog.text
        assert memory.summary == ""
        assert len(memory.messages) == ConversationMemory.SUMMARIZE_THRESHOLD + 1

    def test_manual_summarize_raises_when_openai_errors(
        self, memory, monkeypatch
    ):
        monkeypatch.setattr(
            ConversationMemory,
            "_maybe_summarize",
            lambda self: None,
        )

        for index in range(ConversationMemory.SUMMARIZE_THRESHOLD + 2):
            memory.add_message("user", f"message {index}")

        class DummyChatCompletion:
            @staticmethod
            def create(**_):
                raise ValueError("network issue")

        monkeypatch.setattr(
            conversation_memory_module.openai,
            "ChatCompletion",
            DummyChatCompletion,
        )

        with pytest.raises(RuntimeError, match="summarization failed"):
            memory.summarize_conversation()
