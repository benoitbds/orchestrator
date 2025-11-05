"""Rule based intent parsing used by the /chat endpoint."""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Dict, Optional

from orchestrator import crud

# Keywords are deliberately simple; the goal is only to support a handful of
# deterministic commands for the MVP.
CREATE_KEYWORDS = r"(?:cr[eé]er?|ajoute?r?|create|add)"
UPDATE_KEYWORDS = r"(?:modifie?r?|update|rename|renomm(?:e|er)?|change)"
TYPE_PATTERN = r"epic|capability|feature|us|uc"
CHILD_KEYWORDS = ("us", "user stories", "stories", "uc", "use cases")
CHILD_COUNT_PATTERN = re.compile(
    r"(\d+)\s*(us|user stories|stories|uc|use cases)",
    re.IGNORECASE,
)
CHILD_PARENT_PATTERN = re.compile(
    r"feature\s*(?:#|n[°o]?|num(?:ero)?|id)?\s*(\d+)|\[\s*feature\s*#?(\d+)\s*\]",
    re.IGNORECASE,
)


def _norm_type(raw: str) -> str:
    return raw.upper() if raw.lower() in {"us", "uc"} else raw.capitalize()


def _strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def parse_intent(objective: str) -> Optional[Dict]:
    """Parse a natural language objective into a structured intent."""
    if not objective:
        return None
    obj = objective.strip()
    obj_low = obj.lower()
    obj_norm = _strip_accents(obj).lower()

    if any(verb in obj_norm for verb in ("genere", "generate", "create")) and any(
        keyword in obj_norm for keyword in CHILD_KEYWORDS
    ):
        parent_match = CHILD_PARENT_PATTERN.search(_strip_accents(obj))
        if parent_match:
            parent_id_str = parent_match.group(1) or parent_match.group(2)
            try:
                parent_id = int(parent_id_str)
            except (TypeError, ValueError):
                parent_id = None
            if parent_id is not None:
                count_match = CHILD_COUNT_PATTERN.search(_strip_accents(obj))
                target_count = (
                    int(count_match.group(1)) if count_match else 5
                )
                return {
                    "action": "generate_children",
                    "target": {"type": "Feature", "id": parent_id},
                    "target_type": "US",
                    "target_count": max(1, min(10, target_count)),
                }

    # ----- Create -----------------------------------------------------
    if re.search(CREATE_KEYWORDS, obj_low):
        if any(keyword in obj_low for keyword in ("us", "user stories", "stories", "use cases", "uc")):
            parent_match = CHILD_PARENT_PATTERN.search(_strip_accents(obj))
            if parent_match:
                parent_id_str = parent_match.group(1) or parent_match.group(2)
                try:
                    parent_id = int(parent_id_str)
                except (TypeError, ValueError):
                    parent_id = None
                if parent_id is not None:
                    count_match = CHILD_COUNT_PATTERN.search(_strip_accents(obj))
                    target_count = (
                        int(count_match.group(1)) if count_match else 5
                    )
                    return {
                        "action": "generate_children",
                        "target": {"type": "Feature", "id": parent_id},
                        "target_type": "US",
                        "target_count": max(1, min(10, target_count)),
                    }
        type_match = re.search(TYPE_PATTERN, obj_low)
        if not type_match:
            return None
        item_type = _norm_type(type_match.group(0))
        title_match = re.search(r"['\"]([^'\"]+)['\"]", obj)
        title = title_match.group(1) if title_match else None
        if not title:
            return None
        parent = None
        parent_match = re.search(
            rf"(?:sous|under)\s+(?:l'|la|le)?\s*({TYPE_PATTERN})\s*['\"]([^'\"]+)['\"]",
            obj,
            re.I,
        )
        if parent_match:
            parent = {"type": _norm_type(parent_match.group(1)), "title": parent_match.group(2)}
        desc_match = re.search(
            r"(?:avec description|with description)\s*: ?['\"]([^'\"]+)['\"]",
            obj,
            re.I,
        )
        description = desc_match.group(1) if desc_match else None
        return {
            "action": "create",
            "type": item_type,
            "title": title,
            "parent": parent,
            "description": description,
        }

    # ----- Update -----------------------------------------------------
    if re.search(UPDATE_KEYWORDS, obj_low):
        fields: Dict[str, str] = {}
        # New title
        title_match = re.search(r"renomm[eé]?[^'\"]*['\"]([^'\"]+)['\"]", obj, re.I)
        if not title_match:
            title_match = re.search(
                r"(?:title|titre)[^'\"]*(?:to|en)\s*['\"]([^'\"]+)['\"]",
                obj,
                re.I,
            )
        if title_match:
            fields["title"] = title_match.group(1)
        desc_match = re.search(
            r"description[^'\"]*(?:to|en|:)\s*['\"]([^'\"]+)['\"]",
            obj,
            re.I,
        )
        if desc_match:
            fields["description"] = desc_match.group(1)
        status_match = re.search(
            r"(?:status|statut)[^\w]*?(?:to|en|:)?\s*['\"]?([\w-]+)['\"]?",
            obj,
            re.I,
        )
        if status_match:
            fields["status"] = status_match.group(1)
        if not fields:
            return None

        id_match = re.search(rf"(?:{TYPE_PATTERN})\s*(\d+)", obj_low)
        if not id_match:
            id_match = re.search(r"\b(\d+)\b", obj_low)
        if id_match:
            return {"action": "update", "target": {"id": int(id_match.group(1))}, "fields": fields}
        lookup_match = re.search(rf"({TYPE_PATTERN})\s*['\"]([^'\"]+)['\"]", obj, re.I)
        if lookup_match:
            project_match = re.search(r"(?:projet|project)\s*(\d+)", obj, re.I)
            project_id = int(project_match.group(1)) if project_match else None
            return {
                "action": "update",
                "target": {
                    "type": _norm_type(lookup_match.group(1)),
                    "title": lookup_match.group(2),
                    "project_id": project_id,
                },
                "fields": fields,
            }

    return None


# ---------------------------------------------------------------------------
# Helpers to record intent steps
# ---------------------------------------------------------------------------


def intent_detected(run_id: str, intent: Dict) -> None:
    """Record a successful intent detection step."""
    crud.record_run_step(run_id, "intent_detected", json.dumps(intent))


def intent_error(run_id: str, error: str, detail: Dict | None = None) -> None:
    """Record an intent parsing error."""
    payload = {"error": error}
    if detail:
        payload.update(detail)
    crud.record_run_step(run_id, "intent_error", json.dumps(payload))
