import pytest

from backend.agent.utterances import ask_clarification, reformulate_ack


class TestReformulateAck:
    def test_generates_ack_with_command_focus(self):
        message = "Peux-tu générer 5 US sous la Feature 'Paiement' ?"

        utterance = reformulate_ack(message)

        assert utterance.startswith("Bien reçu. Si je comprends bien, tu veux")
        assert "« générer 5 US sous la Feature 'Paiement' »" in utterance
        assert utterance.endswith("C’est bien ça ?")

    def test_rejects_blank_message(self):
        with pytest.raises(ValueError):
            reformulate_ack("   ")

    def test_truncates_long_messages(self):
        long_request = "Peux-tu créer " + "une tâche très détaillée " * 20 + "?"

        utterance = reformulate_ack(long_request)

        assert "…" in utterance
        assert len(utterance) < 280

    def test_handles_multiline_and_polite_prefixes(self):
        message = "Bonjour\nPeux-tu ajouter une vérification des doublons dans le reporting ?"

        utterance = reformulate_ack(message)

        assert "« ajouter une vérification des doublons dans le reporting »" in utterance
        assert "Bonjour" not in utterance


class TestAskClarification:
    def test_returns_prompt_without_options(self):
        prompt = ask_clarification("clarifier la priorité")

        assert prompt == "Pour préciser : clarifier la priorité ?"

    def test_includes_limited_options(self):
        options = [
            "Option A",
            "Option B",
            "Option C",
            "Option D",
            "Option E",
            "Option F",  # should be ignored due to cap
        ]

        prompt = ask_clarification("quel plan suivre", options)

        assert (
            prompt
            == "Pour être sûr : quel plan suivre ? Choix possibles : « Option A » / « Option B » / "
            "« Option C » / « Option D » / « Option E »"
            "."
        )

    def test_filters_blank_options(self):
        prompt = ask_clarification("quel livrable", ["  ", "MVP", "", "Pilot  "])

        assert (
            prompt
            == "Pour être sûr : quel livrable ? Choix possibles : « MVP » / « Pilot »."
        )

    @pytest.mark.parametrize("question", ["", "   ", 123])
    def test_rejects_invalid_question(self, question):
        with pytest.raises(ValueError):
            ask_clarification(question)  # type: ignore[arg-type]

    def test_rejects_invalid_options_container(self):
        with pytest.raises(ValueError):
            ask_clarification("quel choix", options="not a list")

    def test_rejects_non_string_option(self):
        with pytest.raises(ValueError):
            ask_clarification("quel choix", options=["ok", 2])
