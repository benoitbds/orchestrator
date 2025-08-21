import re
from typing import Dict, Optional

ALLOWED_TYPES = {"feature", "epic", "capability", "us", "uc"}

CREATE_KEYWORDS = r"(?:cr[eé]e|cree|ajoute|add|create)"
UPDATE_KEYWORDS = r"(?:modifie|update|rename|change)"
TYPE_PATTERN = r"epic|capability|feature|us|uc"


def parse_intent(objective: str) -> Optional[Dict]:
    """Parse a natural language objective into a structured intent.

    Returns a dict describing the intent or ``None`` if no intent could be
    determined. Supported intents are simple create/update actions on backlog
    items.
    """
    if not objective:
        return None

    obj_low = objective.lower()

    # --- Create intents -------------------------------------------------
    if re.search(CREATE_KEYWORDS, obj_low):
        type_match = re.search(TYPE_PATTERN, obj_low)
        title_match = re.search(r"[\"']([^\"']+)[\"']", objective)
        project_match = re.search(r"(?:projet|project)\s*(\d+)", obj_low)
        parent_match = re.search(
            r"(?:dans|sous|under)\s+(?:l'|la|le)?(?:epic|capability|feature|us|uc)\s*(\d+)",
            obj_low,
        )
        if not (type_match and title_match and project_match):
            return None
        item_type = type_match.group(0).capitalize()
        return {
            "action": "create",
            "type": item_type,
            "title": title_match.group(1),
            "project_id": int(project_match.group(1)),
            "parent_id": int(parent_match.group(1)) if parent_match else None,
        }

    # --- Update intents -------------------------------------------------
    if re.search(UPDATE_KEYWORDS, obj_low):
        id_match = re.search(r"(?:id|item)\s*(\d+)", obj_low)
        if not id_match:
            return None
        fields: Dict[str, str] = {}
        title_match = re.search(r"(?:titre|title)\s*[\"']([^\"']+)[\"']", objective, re.I)
        if title_match:
            fields["title"] = title_match.group(1)
        desc_match = re.search(r"description\s*[\"']([^\"']+)[\"']", objective, re.I)
        if desc_match:
            fields["description"] = desc_match.group(1)
        status_match = re.search(r"(?:statut|status)\s*([\w-]+)", obj_low)
        if status_match:
            fields["status"] = status_match.group(1)
        if not fields:
            return None
        return {"action": "update", "id": int(id_match.group(1)), "fields": fields}

    return None
