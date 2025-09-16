"""Keyword-driven intent classification with ambiguity cues."""
from __future__ import annotations

from typing import Dict, Iterable, Tuple

_INTENTS: Dict[str, Tuple[str, ...]] = {
    "CREATE_ITEMS": ("crée", "créer", "génère", "ajoute", "create", "generate", "add"),
    "LIST_ITEMS": ("liste", "montre", "list", "show"),
    "SUMMARIZE": ("résume", "recap", "summary"),
    "SMALLTALK": ("bonjour", "merci", "ok", "coucou", "salut"),
    "HELP": ("aide", "how", "comment faire", "help"),
}

_AMBIGUITY_CUES: Tuple[str, ...] = (
    "lequel",
    "laquelle",
    "parmi",
    "quel parent",
    "plusieurs",
    "choisir",
    "which one",
)

_INTENT_PRIORITY = {intent: index for index, intent in enumerate(_INTENTS)}


def _validate_message(user_message: str) -> str:
    if not isinstance(user_message, str):
        raise ValueError("user_message must be a non-empty string")
    cleaned = user_message.strip()
    if not cleaned:
        raise ValueError("user_message must be a non-empty string")
    return cleaned.lower()


def _score_intent(message: str, keywords: Iterable[str]) -> int:
    return sum(1 for keyword in keywords if keyword in message)


def _select_intent(scores: Dict[str, int]) -> Tuple[str, int]:
    return max(
        scores.items(),
        key=lambda item: (item[1], -_INTENT_PRIORITY[item[0]]),
    )


def _compute_confidence(best_score: int, total_hits: int) -> float:
    if total_hits <= 0:
        return 0.0
    return best_score / float(total_hits)


def classify_intent(user_message: str) -> Tuple[str, float, Dict[str, bool | Dict[str, int]]]:
    """Return the most likely intent with a heuristic confidence score."""

    normalised_message = _validate_message(user_message)

    scores: Dict[str, int] = {
        intent: _score_intent(normalised_message, keywords)
        for intent, keywords in _INTENTS.items()
    }

    best_intent, best_score = _select_intent(scores)
    total_hits = sum(scores.values())
    confidence = _compute_confidence(best_score, total_hits)

    if best_score == 0:
        best_intent = "SMALLTALK"

    ambiguity = any(cue in normalised_message for cue in _AMBIGUITY_CUES)

    metadata: Dict[str, bool | Dict[str, int]] = {
        "ambiguity": ambiguity,
        "scores": scores,
    }

    return best_intent, float(confidence), metadata
