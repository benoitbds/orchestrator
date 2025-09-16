import pytest

from backend.agent import handler
from backend.agent.confirm_gate import PENDING, stage_risky_intent


@pytest.fixture(autouse=True)
def clear_pending():
    PENDING.clear()


class StubExecutor:
    def __init__(self, result):
        self.result = result
        self.calls: list[dict] = []

    def __call__(self, payload):
        self.calls.append(dict(payload))
        return self.result


def _make_steps():
    return [
        {
            "tool": "generate",
            "result": {"created": 1, "updated": 0, "deleted": 0},
            "meta": {"scope": "Sprint"},
        }
    ]


class TestHandleUserTurn:
    def test_reformulate_on_smalltalk(self):
        executor = StubExecutor({"steps": _make_steps()})
        run_context = {"execute_tools": executor, "steps": []}

        response = handler.handle_user_turn("Bonjour", None, run_context)

        assert response["type"] == "text"
        assert "Bien reçu" in response["text"]
        assert executor.calls == []

    def test_ask_clarification_when_ambiguous(self):
        executor = StubExecutor({"steps": _make_steps()})
        run_context = {
            "execute_tools": executor,
            "steps": [],
            "clarification_options": ["Ventes", "Support"],
        }

        response = handler.handle_user_turn(
            "Lequel devrions-nous créer ?", None, run_context
        )

        assert response["type"] == "text"
        assert "Choix possibles" in response["text"]
        assert executor.calls == []

    def test_stages_confirmation_when_needed(self):
        executor = StubExecutor({"steps": _make_steps()})
        run_context = {
            "execute_tools": executor,
            "steps": [],
            "last_params": {"count": 2},
            "last_preview": ["Item A", "Item B"],
        }

        response = handler.handle_user_turn(
            "Merci de confirmer l'action create", None, run_context
        )

        assert response["type"] == "text"
        assert "Token" in response["text"]
        assert run_context["pending_token"] in PENDING
        assert executor.calls == []

    def test_resolves_confirmation_and_executes(self):
        executor = StubExecutor({"steps": _make_steps()})
        token = stage_risky_intent({"action": "CREATE_ITEMS"})
        run_context = {
            "execute_tools": executor,
            "steps": [],
            "pending_token": token,
        }

        response = handler.handle_user_turn("confirme", None, run_context)

        assert response["type"] == "text"
        assert "Synthèse" in response["text"]
        assert run_context["pending_token"] is None
        assert executor.calls[0]["action"] == "CREATE_ITEMS"

    def test_cancels_pending_confirmation(self):
        executor = StubExecutor({"steps": _make_steps()})
        token = stage_risky_intent({"action": "CREATE_ITEMS"})
        run_context = {
            "execute_tools": executor,
            "steps": [],
            "pending_token": token,
        }

        response = handler.handle_user_turn("annule", None, run_context)

        assert response == {"type": "text", "text": handler.CANCELLATION_REPLY}
        assert run_context["pending_token"] is None
        assert executor.calls == []

    def test_executes_intent_when_confident(self):
        executor = StubExecutor({"steps": _make_steps()})
        run_context = {
            "execute_tools": executor,
            "steps": [],
            "last_params": {"epic": "Paiement"},
        }

        response = handler.handle_user_turn(
            "Peux-tu créer un backlog ?", None, run_context
        )

        assert "Bien reçu" in response["text"]
        assert "Synthèse" in response["text"]
        assert executor.calls[0]["action"] == "CREATE_ITEMS"
        assert run_context["steps"]

    def test_requires_callable_executor(self):
        with pytest.raises(ValueError):
            handler.handle_user_turn("Hello", None, {"steps": []})

    def test_rejects_blank_message(self):
        executor = StubExecutor({"steps": _make_steps()})
        with pytest.raises(ValueError):
            handler.handle_user_turn("  ", None, {"execute_tools": executor, "steps": []})

