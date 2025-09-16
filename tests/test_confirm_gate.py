import pytest

import backend.agent.confirm_gate as confirm_gate
from backend.agent.confirm_gate import resolve_confirmation, stage_risky_intent


@pytest.fixture(autouse=True)
def clear_pending():
    confirm_gate.PENDING.clear()


class TestStageRiskyIntent:
    def test_stages_payload_and_returns_token(self):
        payload = {"action": "CREATE_ITEMS", "params": {"count": 1}, "preview": ["item"]}

        token = stage_risky_intent(payload)

        assert token in confirm_gate.PENDING
        payload["params"]["count"] = 5

        assert confirm_gate.PENDING[token]["action"] == "CREATE_ITEMS"
        assert confirm_gate.PENDING[token]["params"]["count"] == 1

    @pytest.mark.parametrize(
        "payload, expected_message",
        [
            ("not a dict", "mapping"),
            ({}, "'action'"),
            ({"action": "   "}, "'action'"),
            ({"action": "CREATE", "params": []}, "'params'"),
            ({"action": "CREATE", "preview": {}}, "'preview'"),
        ],
    )
    def test_rejects_invalid_payload(self, payload, expected_message):
        with pytest.raises(ValueError, match=expected_message):
            stage_risky_intent(payload)  # type: ignore[arg-type]


class TestResolveConfirmation:
    def test_confirms_pending_intent(self):
        payload = {"action": "DELETE", "params": {}}
        token = stage_risky_intent(payload)

        result = resolve_confirmation(token, "Oui")

        assert result["status"] == "confirmed"
        assert result["payload"] == {"action": "DELETE", "params": {}}
        assert token not in confirm_gate.PENDING

    def test_cancels_pending_intent(self):
        token = stage_risky_intent({"action": "UPDATE"})

        result = resolve_confirmation(token, "non")

        assert result == {"status": "cancelled"}
        assert token not in confirm_gate.PENDING

    def test_returns_awaiting_for_unclear_reply(self):
        token = stage_risky_intent({"action": "RUN"})

        result = resolve_confirmation(token, "maybe")

        assert result == {"status": "awaiting"}
        assert token in confirm_gate.PENDING

    def test_returns_invalid_token_when_missing(self):
        result = resolve_confirmation("missing-token", "yes")

        assert result == {"status": "invalid_token"}

    @pytest.mark.parametrize("token", ["", "   ", None])
    def test_requires_non_empty_token(self, token):
        with pytest.raises(ValueError):
            resolve_confirmation(token, "yes")  # type: ignore[arg-type]

    @pytest.mark.parametrize("reply", ["", "   ", None])
    def test_requires_non_empty_reply(self, reply):
        token = stage_risky_intent({"action": "TEST"})

        with pytest.raises(ValueError):
            resolve_confirmation(token, reply)  # type: ignore[arg-type]
