import pytest

from backend.agent.nlu import classify_intent


class TestClassifyIntent:
    def test_identifies_create_items_intent(self):
        intent, confidence, metadata = classify_intent("Peux-tu créer et ajouter un item ?")

        assert intent == "CREATE_ITEMS"
        assert confidence == 1.0
        assert metadata["scores"]["CREATE_ITEMS"] >= 2
        assert metadata["ambiguity"] is False

    def test_flags_ambiguity_keywords(self):
        intent, confidence, metadata = classify_intent("Lequel dois-je ajouter ?")

        assert metadata["ambiguity"] is True
        assert intent == "CREATE_ITEMS"
        assert confidence == 1.0

    def test_handles_mixed_intent_scores(self):
        intent, confidence, metadata = classify_intent("Peux-tu lister et créer les éléments ?")

        assert intent == "CREATE_ITEMS"
        assert pytest.approx(confidence, rel=1e-6) == 0.5
        assert metadata["scores"]["LIST_ITEMS"] >= 1
        assert metadata["scores"]["CREATE_ITEMS"] >= 1

    @pytest.mark.parametrize("message", ["", "   ", None])
    def test_rejects_invalid_messages(self, message):
        with pytest.raises(ValueError):
            classify_intent(message)  # type: ignore[arg-type]

    def test_defaults_to_smalltalk_when_no_matches(self):
        intent, confidence, metadata = classify_intent("This text has no keywords")

        assert intent == "SMALLTALK"
        assert confidence == 0.0
        assert all(score == 0 for score in metadata["scores"].values())
