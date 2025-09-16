"""Utilities for staging and resolving risky intents pending confirmation."""
from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any, Dict, Mapping
from uuid import uuid4

AFFIRMATIVE_REPLIES = {
    "oui",
    "yes",
    "y",
    "ok",
    "go",
    "confirm",
    "confirme",
}
NEGATIVE_REPLIES = {
    "non",
    "no",
    "n",
    "cancel",
    "annule",
}

PENDING: Dict[str, Dict[str, Any]] = {}
_LOCK = RLock()


def _normalise_reply(user_reply: str) -> str:
    if not isinstance(user_reply, str):
        raise ValueError("user_reply must be a non-empty string")
    reply = user_reply.strip().lower()
    if not reply:
        raise ValueError("user_reply must be a non-empty string")
    return reply


def _validate_payload(intent_payload: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(intent_payload, Mapping):
        raise ValueError("intent_payload must be a mapping with an action")

    payload_dict = dict(intent_payload)
    action = payload_dict.get("action")
    if not isinstance(action, str) or not action.strip():
        raise ValueError("intent_payload must include a non-empty 'action'")

    if "params" in payload_dict and not isinstance(payload_dict["params"], Mapping):
        raise ValueError("intent_payload 'params' must be a mapping if provided")

    if "preview" in payload_dict and not isinstance(payload_dict["preview"], list):
        raise ValueError("intent_payload 'preview' must be a list if provided")

    return deepcopy(payload_dict)


def stage_risky_intent(intent_payload: Mapping[str, Any]) -> str:
    """Store *intent_payload* until confirmation and return its token."""

    payload = _validate_payload(intent_payload)

    token = str(uuid4())
    with _LOCK:
        PENDING[token] = payload
    return token


def resolve_confirmation(token: str, user_reply: str) -> Dict[str, Any]:
    """Resolve a staged intent by interpreting *user_reply* for *token*."""

    if not isinstance(token, str) or not token.strip():
        raise ValueError("token must be a non-empty string")

    reply = _normalise_reply(user_reply)

    with _LOCK:
        payload = PENDING.get(token)
        if payload is None:
            return {"status": "invalid_token"}

        if reply in AFFIRMATIVE_REPLIES:
            del PENDING[token]
            return {"status": "confirmed", "payload": deepcopy(payload)}

        if reply in NEGATIVE_REPLIES:
            del PENDING[token]
            return {"status": "cancelled"}

    return {"status": "awaiting"}
