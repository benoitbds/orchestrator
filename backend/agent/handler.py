"""High-level orchestration for a single chat turn."""
from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping, Sequence
import json
from typing import Any

from .confirm_gate import (
    AFFIRMATIVE_REPLIES,
    NEGATIVE_REPLIES,
    resolve_confirmation,
    stage_risky_intent,
)
from .dialogue_policy import dialogue_policy
from .narrator import narrate_steps
from .nlu import classify_intent
from .utterances import ask_clarification, reformulate_ack


DEFAULT_CLARIFICATION_QUESTION = "Sous quel Epic dois-je créer ces éléments ?"
DEFAULT_CLARIFICATION_OPTIONS = ("Ventes", "Support", "Facturation")
CONFIRMATION_PROMPT = "Avant d’exécuter, confirme-tu ? (Oui/Non)"
CANCELLATION_REPLY = "Compris, j’annule cette action."
AWAITING_REPLY = "Peux-tu répondre par Oui ou Non pour que je continue ?"
INVALID_TOKEN_REPLY = (
    "Je ne retrouve pas cette action à confirmer. Relance ta demande pour poursuivre."
)
EXECUTION_ERROR_REPLY = (
    "*(Erreur : l’action n’a pas pu s’exécuter. Merci de réessayer plus tard.)*"
)


def _validate_message(user_message: str) -> str:
    if not isinstance(user_message, str) or not user_message.strip():
        raise ValueError("user_message must be a non-empty string")
    return user_message.strip()


def _prepare_run_context(run_context: MutableMapping[str, Any] | None) -> MutableMapping[str, Any]:
    if run_context is None:
        raise ValueError("run_context must be provided")
    if not isinstance(run_context, MutableMapping):
        raise TypeError("run_context must be a mutable mapping")

    steps = run_context.get("steps")
    if steps is None:
        run_context["steps"] = []
    elif not isinstance(steps, list):
        run_context["steps"] = list(steps)

    return run_context


def _resolve_executor(
    provided_executor: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None,
    run_context: MutableMapping[str, Any],
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    executor = provided_executor or run_context.get("execute_tools")
    if not callable(executor):
        raise ValueError("execute_tools must be a callable returning a mapping")
    return executor  # type: ignore[return-value]


def _normalise_params(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _normalise_preview(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return [value]


def _format_preview(preview: Sequence[Any]) -> str:
    if not preview:
        return "Prévisualisation: (aucune)"
    try:
        rendered = json.dumps(preview, ensure_ascii=False)
    except TypeError:
        rendered = str(preview)
    return f"Prévisualisation: {rendered}"


def _build_payload(intent: str, run_context: MutableMapping[str, Any]) -> dict[str, Any]:
    payload = {
        "action": intent,
        "params": _normalise_params(run_context.get("last_params")),
    }

    preview = _normalise_preview(run_context.get("last_preview"))
    if preview:
        payload["preview"] = preview

    return payload


def _execute_tools(
    executor: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    payload: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]], str | None]:
    try:
        result = executor(payload)
    except Exception:
        return [], EXECUTION_ERROR_REPLY

    if not isinstance(result, Mapping):
        return [], EXECUTION_ERROR_REPLY

    steps = result.get("steps")
    if isinstance(steps, Sequence):
        return [dict(step) for step in steps if isinstance(step, Mapping)], None

    return [], None


def _clarification_text(run_context: Mapping[str, Any]) -> tuple[str, Sequence[str]]:
    question = run_context.get("clarification_question", DEFAULT_CLARIFICATION_QUESTION)
    if not isinstance(question, str) or not question.strip():
        question = DEFAULT_CLARIFICATION_QUESTION

    options_value = run_context.get("clarification_options")
    if isinstance(options_value, Sequence) and not isinstance(options_value, (str, bytes, bytearray)):
        options = [
            str(option)
            for option in options_value
            if isinstance(option, str) and option.strip()
        ]
        if options:
            return question.strip(), options

    return question.strip(), DEFAULT_CLARIFICATION_OPTIONS


def _handle_confirmation_request(
    user_message: str,
    run_context: MutableMapping[str, Any],
    executor: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, str]:
    pending_token = run_context.get("pending_token")

    if not pending_token:
        intent = (
            run_context.get("pending_intent")
            or run_context.get("last_intent")
            or run_context.get("last_action")
            or "EXECUTE"
        )
        payload = _build_payload(str(intent), run_context)
        if not payload.get("action"):
            payload["action"] = "EXECUTE"

        token = stage_risky_intent(payload)
        run_context["pending_token"] = token
        preview = _format_preview(payload.get("preview", []))
        text = f"{CONFIRMATION_PROMPT}\n{preview}\nToken: {token}"
        return {"type": "text", "text": text}

    status = resolve_confirmation(pending_token, user_message)
    if status["status"] == "confirmed":
        run_context["pending_token"] = None
        payload = status.get("payload") or {}
        steps, error = _execute_tools(executor, payload)
        if error:
            return {"type": "text", "text": error}
        run_context["steps"].extend(steps)
        return {"type": "text", "text": narrate_steps(steps)}

    if status["status"] == "cancelled":
        run_context["pending_token"] = None
        return {"type": "text", "text": CANCELLATION_REPLY}

    if status["status"] == "invalid_token":
        run_context["pending_token"] = None
        return {"type": "text", "text": INVALID_TOKEN_REPLY}

    return {"type": "text", "text": AWAITING_REPLY}


def _handle_execution(
    user_message: str,
    intent: str,
    run_context: MutableMapping[str, Any],
    executor: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, str]:
    payload = _build_payload(intent, run_context)
    steps, error = _execute_tools(executor, payload)
    if error:
        return {"type": "text", "text": error}

    run_context["steps"].extend(steps)
    acknowledgement = reformulate_ack(user_message)
    narration = narrate_steps(steps)
    return {"type": "text", "text": f"{acknowledgement}\n{narration}"}


def handle_user_turn(
    user_message: str,
    memory: Any,
    run_context: MutableMapping[str, Any] | None,
    execute_tools: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, str]:
    """Process a user message and return the assistant response payload."""

    message = _validate_message(user_message)
    context = _prepare_run_context(run_context)
    executor = _resolve_executor(execute_tools, context)

    intent, confidence, signals = classify_intent(message)
    context["last_intent"] = intent

    has_pending = context.get("pending_token") is not None
    long_steps = len(context.get("steps", []))
    policy = dialogue_policy(message, intent, confidence, has_pending, long_steps)
    decision = policy["decision"]

    if has_pending and decision != "ASK_CONFIRMATION":
        reply = message.lower()
        keywords = AFFIRMATIVE_REPLIES | NEGATIVE_REPLIES
        if any(keyword in reply for keyword in keywords):
            decision = "ASK_CONFIRMATION"

    if decision == "REFORMULATE":
        return {"type": "text", "text": reformulate_ack(message)}

    if decision == "ASK_CLARIFICATION":
        question, options = _clarification_text({**context, **signals})
        return {"type": "text", "text": ask_clarification(question, list(options))}

    if decision == "ASK_CONFIRMATION":
        return _handle_confirmation_request(message, context, executor)

    if decision == "SUMMARIZE":
        return {"type": "text", "text": narrate_steps(context.get("steps", []))}

    return _handle_execution(message, intent, context, executor)
