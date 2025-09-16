"""Convert tool execution steps into a concise French recap."""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

_MAX_HIGHLIGHTS = 6
_DEFAULT_MESSAGE = "Aucune action effectuée pour l’instant."
_HEADER = "Synthèse de l’exécution :"
_SUGGESTION = (
    "Prochaine étape suggérée : générer les US pour la Feature la plus prioritaire, "
    "ou demander une vérification de couverture."
)


def _validate_steps(steps: Sequence[Mapping[str, Any]] | Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    if steps is None or isinstance(steps, (str, bytes)):
        raise ValueError("steps must be an iterable of mappings")

    validated: list[Mapping[str, Any]] = []
    for index, step in enumerate(steps):
        if not isinstance(step, Mapping):
            raise ValueError(f"step at index {index} must be a mapping")
        validated.append(step)
    return validated


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _format_duration(step: Mapping[str, Any]) -> str:
    duration_ms = step.get("duration_ms")
    duration = _safe_int(duration_ms)
    if duration <= 0:
        return ""
    seconds = duration / 1000
    if seconds >= 1:
        return f"{seconds:.1f}s"
    return f"{duration}ms"


def _format_scope(meta: Any) -> str:
    if not isinstance(meta, Mapping):
        return ""
    parts: list[str] = []
    for key, value in meta.items():
        if value is None:
            continue
        parts.append(f"{key}:{value}")
    return " / ".join(parts)


def _format_changes(result: Any) -> str:
    if not isinstance(result, Mapping):
        return ""
    items: list[str] = []
    created = _safe_int(result.get("created"))
    updated = _safe_int(result.get("updated"))
    deleted = _safe_int(result.get("deleted"))
    if created:
        items.append(f"{created} créés")
    if updated:
        items.append(f"{updated} modifiés")
    if deleted:
        items.append(f"{deleted} supprimés")
    return " ; ".join(items)


def _format_highlight(step: Mapping[str, Any]) -> str:
    tool = str(step.get("tool", "?") or "?").strip()
    scope = _format_scope(step.get("meta"))
    duration = _format_duration(step)
    changes = _format_changes(step.get("result"))

    details = [detail for detail in [scope, duration] if detail]
    highlight = f"• {tool}"
    if details:
        highlight += f" ({' ; '.join(details)})"
    if changes:
        highlight += f" → {changes}"
    return highlight


def narrate_steps(steps: Sequence[Mapping[str, Any]] | Iterable[Mapping[str, Any]]) -> str:
    """Return a short French recap for tool execution steps."""

    validated_steps = _validate_steps(steps)
    if not validated_steps:
        return _DEFAULT_MESSAGE

    total_created = total_updated = total_deleted = 0
    highlights: list[str] = []

    for step in validated_steps:
        result = step.get("result", {})
        total_created += _safe_int(result.get("created"))
        total_updated += _safe_int(result.get("updated"))
        total_deleted += _safe_int(result.get("deleted"))
        highlights.append(_format_highlight(step))

    recap_lines = [_HEADER, *highlights[:_MAX_HIGHLIGHTS]]
    recap_lines.append(
        f"→ Total: {total_created} créés, {total_updated} modifiés, {total_deleted} supprimés."
    )
    recap_lines.append(_SUGGESTION)
    return "\n".join(recap_lines)
