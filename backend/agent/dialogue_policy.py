"""Simple dialogue policy module for orchestrator backend."""
from __future__ import annotations

from typing import Dict, Iterable, Literal, Tuple

Decision = Literal[
    "REFORMULATE",
    "ASK_CLARIFICATION",
    "ASK_CONFIRMATION",
    "EXECUTE_INTENT",
    "SUMMARIZE",
]

_CONFIRMATION_KEYWORDS: Tuple[str, ...] = ("confirm", "confirme")
_RECAP_KEYWORDS: Tuple[str, ...] = (
    "résume",
    "resume",
    "recap",
    "qu'as-tu fait",
    "qu as tu fait",
    "what have you done",
)
_AMBIGUITY_KEYWORDS: Tuple[str, ...] = (
    "lequel",
    "laquelle",
    "parmi",
    "quel parent",
    "plusieurs",
)


def _validate_inputs(
    user_message: str,
    intent: str,
    confidence: float,
    has_pending_risky_action: bool,
    long_run_steps: int,
) -> tuple[str, str, float]:
    if not isinstance(user_message, str) or not user_message.strip():
        raise ValueError("user_message must be a non-empty string")
    if not isinstance(intent, str) or not intent.strip():
        raise ValueError("intent must be a non-empty string")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ValueError("confidence must be a float between 0 and 1")
    numeric_confidence = float(confidence)
    if not 0.0 <= numeric_confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if not isinstance(has_pending_risky_action, bool):
        raise ValueError("has_pending_risky_action must be a boolean")
    if (
        not isinstance(long_run_steps, int)
        or isinstance(long_run_steps, bool)
        or long_run_steps < 0
    ):
        raise ValueError("long_run_steps must be a non-negative integer")

    return user_message.strip(), intent.strip(), numeric_confidence


def _contains_keyword(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _decision(decision: Decision, reason: str) -> Dict[str, Decision | str]:
    return {"decision": decision, "reason": reason}


def _should_clarify_low_confidence(confidence: float) -> bool:
    return confidence < 0.5


def _should_request_confirmation(
    has_pending_risky_action: bool, message_lower: str
) -> bool:
    return has_pending_risky_action or _contains_keyword(
        message_lower, _CONFIRMATION_KEYWORDS
    )


def _should_summarize(long_run_steps: int, message_lower: str) -> bool:
    return long_run_steps > 6 or _contains_keyword(message_lower, _RECAP_KEYWORDS)


def _should_clarify_ambiguity(message_lower: str) -> bool:
    return _contains_keyword(message_lower, _AMBIGUITY_KEYWORDS)


def _should_reformulate(intent_upper: str) -> bool:
    return intent_upper == "SMALLTALK"


def dialogue_policy(
    user_message: str,
    intent: str,
    confidence: float,
    has_pending_risky_action: bool,
    long_run_steps: int,
) -> Dict[str, Decision | str]:
    """Return the next assistant decision based on lightweight heuristics."""

    cleaned_message, cleaned_intent, numeric_confidence = _validate_inputs(
        user_message,
        intent,
        confidence,
        has_pending_risky_action,
        long_run_steps,
    )

    message_lower = cleaned_message.lower()
    normalized_intent = cleaned_intent.upper()

    if _should_clarify_low_confidence(numeric_confidence):
        return _decision("ASK_CLARIFICATION", "Low intent confidence")

    if _should_request_confirmation(has_pending_risky_action, message_lower):
        return _decision("ASK_CONFIRMATION", "Confirmation gate required")

    if _should_summarize(long_run_steps, message_lower):
        return _decision("SUMMARIZE", "User requested recap or run is long")

    if _should_clarify_ambiguity(message_lower):
        return _decision("ASK_CLARIFICATION", "Ambiguity keywords detected")

    if _should_reformulate(normalized_intent):
        return _decision("REFORMULATE", "Smalltalk or ack")

    return _decision("EXECUTE_INTENT", "Confident actionable intent")
