import pytest

from backend.agent.narrator import narrate_steps


class TestNarrateSteps:
    def test_builds_recap_with_highlights_and_totals(self):
        steps = [
            {
                "tool": "generate_items_from_parent",
                "duration_ms": 1600,
                "result": {"created": 3, "updated": 0, "deleted": 0},
                "meta": {"parent": "Epic Vente"},
            },
            {
                "tool": "cleanup_items",
                "duration_ms": 450,
                "result": {"updated": "2", "deleted": 1},
                "meta": {"scope": "Sprint 5"},
            },
        ]

        recap = narrate_steps(steps)

        assert recap.startswith("Synthèse de l’exécution :")
        assert "• generate_items_from_parent" in recap
        assert "parent:Epic Vente" in recap
        assert "450ms" in recap
        assert "→ Total: 3 créés, 2 modifiés, 1 supprimés." in recap

    def test_returns_default_message_when_no_steps(self):
        assert (
            narrate_steps([])
            == "Aucune action effectuée pour l’instant."
        )

    def test_rejects_non_iterable_steps(self):
        with pytest.raises(ValueError):
            narrate_steps("not a valid steps list")

    def test_rejects_non_mapping_step_entry(self):
        with pytest.raises(ValueError):
            narrate_steps([{"tool": "ok"}, "bad-entry"])
