import pytest

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
