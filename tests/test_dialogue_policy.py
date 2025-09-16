"""Unit tests for the dialogue policy heuristics."""
import pytest

from backend.agent.dialogue_policy import dialogue_policy


class TestDialoguePolicyDecisions:
    def test_low_confidence_requests_clarification(self):
        result = dialogue_policy(
            user_message="Please help me",
            intent="SOME_INTENT",
            confidence=0.3,
            has_pending_risky_action=False,
            long_run_steps=0,
        )

        assert result == {
            "decision": "ASK_CLARIFICATION",
            "reason": "Low intent confidence",
        }

    def test_risky_action_requires_confirmation(self):
        result = dialogue_policy(
            user_message="Let's do it",
            intent="EXECUTE",
            confidence=0.9,
            has_pending_risky_action=True,
            long_run_steps=0,
        )

        assert result["decision"] == "ASK_CONFIRMATION"
        assert "Confirmation" in result["reason"]

    def test_summary_keywords_trigger_summarize(self):
        result = dialogue_policy(
            user_message="Can you recap what have you done so far?",
            intent="PROGRESS",
            confidence=0.9,
            has_pending_risky_action=False,
            long_run_steps=1,
        )

        assert result == {
            "decision": "SUMMARIZE",
            "reason": "User requested recap or run is long",
        }

    def test_long_run_steps_trigger_summarize(self):
        result = dialogue_policy(
            user_message="continue",
            intent="PROGRESS",
            confidence=0.9,
            has_pending_risky_action=False,
            long_run_steps=7,
        )

        assert result["decision"] == "SUMMARIZE"

    def test_smalltalk_intent_reformulates(self):
        result = dialogue_policy(
            user_message="Hello there!",
            intent="smalltalk",
            confidence=0.8,
            has_pending_risky_action=False,
            long_run_steps=0,
        )

        assert result == {
            "decision": "REFORMULATE",
            "reason": "Smalltalk or ack",
        }

    def test_ambiguity_keywords_request_clarification(self):
        result = dialogue_policy(
            user_message="Laquelle devrions-nous choisir?",
            intent="DECIDE",
            confidence=0.8,
            has_pending_risky_action=False,
            long_run_steps=0,
        )

        assert result == {
            "decision": "ASK_CLARIFICATION",
            "reason": "Ambiguity keywords detected",
        }

    def test_default_executes_intent(self):
        result = dialogue_policy(
            user_message="Please create the report",
            intent="GENERATE_REPORT",
            confidence=0.9,
            has_pending_risky_action=False,
            long_run_steps=0,
        )

        assert result == {
            "decision": "EXECUTE_INTENT",
            "reason": "Confident actionable intent",
        }


class TestDialoguePolicyValidation:
    @pytest.mark.parametrize("message", ["", "   "])
    def test_rejects_empty_message(self, message):
        with pytest.raises(ValueError):
            dialogue_policy(
                user_message=message,
                intent="PLAN",
                confidence=0.5,
                has_pending_risky_action=False,
                long_run_steps=0,
            )

    def test_rejects_invalid_confidence(self):
        with pytest.raises(ValueError):
            dialogue_policy(
                user_message="Hi",
                intent="PLAN",
                confidence=1.5,
                has_pending_risky_action=False,
                long_run_steps=0,
            )

    def test_rejects_negative_long_run_steps(self):
        with pytest.raises(ValueError):
            dialogue_policy(
                user_message="Hi",
                intent="PLAN",
                confidence=0.8,
                has_pending_risky_action=False,
                long_run_steps=-1,
            )
