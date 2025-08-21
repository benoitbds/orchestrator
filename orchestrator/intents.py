"""Rule based intent parsing used by the /chat endpoint."""

from __future__ import annotations

import re
from typing import Dict, Optional

# Keywords are deliberately simple; the goal is only to support a handful of
# deterministic commands for the MVP.
CREATE_KEYWORDS = r"(?:cr[eé]er?|ajoute?r?|create|add)"
UPDATE_KEYWORDS = r"(?:modifie?r?|update|rename|change)"
TYPE_PATTERN = r"epic|capability|feature|us|uc"


ALLOWED_TYPES = {"epic", "capability", "feature", "us", "uc"}


def _parse_common(obj: str) -> tuple[Optional[str], Optional[str], Optional[int], Optional[int]]:
    """Extract basic elements shared by create/update intents."""

    type_match = re.search(TYPE_PATTERN, obj, re.I)
    item_type = type_match.group(0).capitalize() if type_match else None
    title_match = re.search(r"['\"]([^'\"]+)['\"]", obj)
    title = title_match.group(1) if title_match else None
    project_match = re.search(r"(?:projet|project)\s*(\d+)", obj, re.I)
    project_id = int(project_match.group(1)) if project_match else None
    parent_match = re.search(
        r"(?:dans|sous|under)\s+(?:l'|la|le)?(?:epic|capability|feature|us|uc)\s*(\d+)",
        obj,
        re.I,
    )
    parent_id = int(parent_match.group(1)) if parent_match else None
    return item_type, title, project_id, parent_id


def parse_intent(objective: str) -> Optional[Dict]:
    """Parse a natural language objective into a structured intent."""

    if not objective:
        return None

    obj = objective.strip()
    obj_low = obj.lower()

    # ----- Create -----------------------------------------------------
    if re.search(CREATE_KEYWORDS, obj_low):
        item_type, title, project_id, parent_id = _parse_common(obj)
        if not (item_type and title):
            return None
        return {
            "action": "create",
            "type": item_type,
            "title": title,
            "project_id": project_id,
            "parent_id": parent_id,
        }

    # ----- Update -----------------------------------------------------
    if re.search(UPDATE_KEYWORDS, obj_low):
        fields: Dict[str, str] = {}
        # New title/description/status
        title_match = re.search(r"(?:titre|title)[^'\"]*['\"]([^'\"]+)['\"]", obj, re.I)
        if title_match:
            fields["title"] = title_match.group(1)
        desc_match = re.search(r"description[^'\"]*['\"]([^'\"]+)['\"]", obj, re.I)
        if desc_match:
            fields["description"] = desc_match.group(1)
        status_match = re.search(r"(?:statut|status)\s*([\w-]+)", obj_low)
        if status_match:
            fields["status"] = status_match.group(1)
        if not fields:
            return None

        # Prefer explicit numeric id
        id_match = re.search(r"(?:epic|capability|feature|us|uc)\s*(\d+)", obj_low)
        if not id_match:
            id_match = re.search(r"\b(\d+)\b", obj_low)
        if id_match:
            return {"action": "update", "id": int(id_match.group(1)), "fields": fields}

        # Fallback: lookup by type + quoted title
        item_type, title, project_id, _ = _parse_common(obj)
        if item_type and title:
            return {
                "action": "update",
                "lookup": {"type": item_type, "title": title, "project_id": project_id},
                "fields": fields,
            }

    return None

