import pytest

from backend.agent.utterances import reformulate_ack


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
