"""Natural-language utterance builders for the backend agent."""
from __future__ import annotations

import re
from typing import Final, Iterable, Sequence

_ACK_PREFIX: Final[str] = "Bien reçu."
_REFORMULATION_PREFIX: Final[str] = "Si je comprends bien, tu veux"
_ACK_SUFFIX: Final[str] = "C’est bien ça ?"
_MAX_FOCUS_LENGTH: Final[int] = 160

_QUOTED_TEXT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:[\"“”«»])([^\"“”«»]+)(?:[\"“”«»])|(?:'([^']+)')"
)

_COMMAND_START_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\b(?:crée|créer|génère|générer|ajoute|ajouter)\b", re.IGNORECASE),
    re.compile(r"\b(?:liste|lister|montre|montrer|affiche|afficher|show|list)\b", re.IGNORECASE),
    re.compile(r"\b(?:résume|résumer|recap|synthétise|summarize)\b", re.IGNORECASE),
)

_GREETING_PREFIX_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^(?:bonjour|salut|coucou|hey|hello)\b[ ,!:-]*", re.IGNORECASE),
)

_REQUEST_PREFIX_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(
        r"^(?:peux[- ]tu|pourrais[- ]tu|peux[- ]vous|pourriez[- ]vous|est[- ]ce que tu peux|tu peux|svp|stp|please|merci de|merci d'|merci pour|merci)\b[ ,:;-]*",
        re.IGNORECASE,
    ),
)

_PRONOUN_PREFIX_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(?:me|m'|moi|nous)\s+", re.IGNORECASE)

_WHITESPACE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\s+")
_MAX_OPTIONS: Final[int] = 5


def _validate_user_message(user_message: str) -> str:
    if not isinstance(user_message, str):
        raise ValueError("user_message must be a non-empty string")
    cleaned = user_message.strip()
    if not cleaned:
        raise ValueError("user_message must be a non-empty string")
    return cleaned


def _condense_whitespace(text: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", text).strip()


def _strip_politeness_prefix(message: str) -> str:
    trimmed = message.lstrip()

    for pattern in _GREETING_PREFIX_PATTERNS:
        match = pattern.match(trimmed)
        if match:
            trimmed = trimmed[match.end() :].lstrip()

    changed = True
    while changed:
        changed = False
        for pattern in _REQUEST_PREFIX_PATTERNS:
            match = pattern.match(trimmed)
            if match:
                trimmed = trimmed[match.end() :].lstrip()
                changed = True

    pronoun_match = _PRONOUN_PREFIX_PATTERN.match(trimmed)
    if pronoun_match:
        trimmed = trimmed[pronoun_match.end() :].lstrip()

    return trimmed or message


def _strip_trailing_punctuation(text: str) -> str:
    return text.rstrip(" .!?;:")


def _truncate_focus(text: str, max_length: int = _MAX_FOCUS_LENGTH) -> str:
    if len(text) <= max_length:
        return text
    truncated = text[:max_length].rstrip()
    last_space = truncated.rfind(" ")
    if last_space > 40:  # keep a reasonable amount of context
        truncated = truncated[:last_space]
    return truncated.rstrip(" ,;:") + "…"


def _wrap_focus(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("«") and cleaned.endswith("»"):
        return cleaned
    return f"« {cleaned} »"


def _validate_prompt_component(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")
    cleaned = _condense_whitespace(value.strip())
    if not cleaned:
        raise ValueError(f"{field_name} must be a non-empty string")
    return _strip_trailing_punctuation(cleaned)


def _normalise_options(options: Sequence[str]) -> list[str]:
    cleaned_options: list[str] = []
    for raw_option in options:
        if not isinstance(raw_option, str):
            raise ValueError("options must contain only strings")
        stripped = raw_option.strip()
        if not stripped:
            continue
        normalised = _validate_prompt_component(stripped, field_name="option")
        if normalised:
            cleaned_options.append(normalised)
        if len(cleaned_options) >= _MAX_OPTIONS:
            break
    return cleaned_options


def _extract_quoted_focus(message: str) -> str | None:
    match = _QUOTED_TEXT_PATTERN.search(message)
    if match:
        for group in match.groups():
            if group:
                return group.strip()
    return None


def _extract_command_focus(message: str) -> str | None:
    for pattern in _COMMAND_START_PATTERNS:
        match = pattern.search(message)
        if match:
            return message[match.start() :].strip()
    return None


def _extract_focus(message: str) -> str:
    focus_from_command = _extract_command_focus(message)
    if focus_from_command:
        return focus_from_command

    quoted = _extract_quoted_focus(message)
    if quoted:
        return quoted

    return _strip_politeness_prefix(message)


def reformulate_ack(user_message: str) -> str:
    """Return a short acknowledgement with a reformulated intent hint."""

    validated_message = _validate_user_message(user_message)
    focus = _extract_focus(validated_message)
    focus = _condense_whitespace(focus)
    focus = _strip_trailing_punctuation(focus)
    if not focus:
        focus = validated_message
    focus = _truncate_focus(focus)
    wrapped_focus = _wrap_focus(focus)

    return f"{_ACK_PREFIX} {_REFORMULATION_PREFIX} {wrapped_focus}. {_ACK_SUFFIX}"


def _format_options(options: Iterable[str]) -> str:
    return " / ".join(f"« {option} »" for option in options)


def ask_clarification(
    what_is_unclear: str, options: Sequence[str] | None = None
) -> str:
    """Return a concise clarification prompt with optional choice hints."""

    question = _validate_prompt_component(
        what_is_unclear, field_name="what_is_unclear"
    )

    if options is None:
        return f"Pour préciser : {question} ?"

    if not isinstance(options, Sequence) or isinstance(options, (str, bytes)):
        raise ValueError("options must be a sequence of strings")

    cleaned_options = _normalise_options(options)

    if not cleaned_options:
        return f"Pour préciser : {question} ?"

    formatted_options = _format_options(cleaned_options)
    return (
        f"Pour être sûr : {question} ? Choix possibles : {formatted_options}."
    )
