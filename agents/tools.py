"""LLM tool specifications and handlers for backlog management."""
from __future__ import annotations

from typing import Any, Dict, Callable, Awaitable

from pydantic import BaseModel, ValidationError

from orchestrator import crud
from orchestrator.models import (
    EpicCreate,
    CapabilityCreate,
    FeatureCreate,
    USCreate,
    UCCreate,
    BacklogItemUpdate,
)

# ---------------------------------------------------------------------------
# Tool schemas (OpenAI function calling format)
# ---------------------------------------------------------------------------

create_item_spec = {
    "name": "create_item",
    "description": "Create a backlog item in the given project.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "type": {
                "type": "string",
                "enum": ["Epic", "Capability", "Feature", "US", "UC"],
            },
            "project_id": {"type": "integer"},
            "parent_id": {"type": "integer", "nullable": True},
        },
        "required": ["title", "type", "project_id"],
    },
}

update_item_spec = {
    "name": "update_item",
    "description": "Update fields of an existing backlog item.",
    "parameters": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "status": {"type": "string"},
            "parent_id": {"type": "integer"},
        },
        "required": ["id"],
    },
}

find_item_spec = {
    "name": "find_item",
    "description": "Search items by text within a project and/or type.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "project_id": {"type": "integer"},
            "type": {
                "type": "string",
                "enum": ["Epic", "Capability", "Feature", "US", "UC"],
            },
        },
        "required": ["query", "project_id"],
    },
}

TOOLS = [create_item_spec, update_item_spec, find_item_spec]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _CreateArgs(BaseModel):
    title: str
    type: str
    project_id: int
    parent_id: int | None = None

class _UpdateArgs(BaseModel):
    id: int
    title: str | None = None
    description: str | None = None
    status: str | None = None
    parent_id: int | None = None

class _FindArgs(BaseModel):
    query: str
    project_id: int
    type: str | None = None

_ALLOWED_PARENT = {
    "Capability": ["Epic"],
    "Feature": ["Epic", "Capability"],
    "US": ["Feature"],
    "UC": ["US"],
}

_MODEL_MAP = {
    "Epic": EpicCreate,
    "Capability": CapabilityCreate,
    "Feature": FeatureCreate,
    "US": USCreate,
    "UC": UCCreate,
}

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def create_item_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Validate args and create a backlog item."""
    try:
        data = _CreateArgs(**args)
        if data.parent_id is not None:
            parent = crud.get_item(data.parent_id)
            if not parent or parent.project_id != data.project_id:
                raise ValueError("invalid parent_id")
            allowed = _ALLOWED_PARENT.get(data.type, [])
            if parent.type not in allowed:
                raise ValueError("invalid hierarchy")
        Model = _MODEL_MAP[data.type]
        item = Model(
            title=data.title,
            description="",
            project_id=data.project_id,
            parent_id=data.parent_id,
        )
        created = crud.create_item(item)
        return {
            "ok": True,
            "item_id": created.id,
            "type": created.type,
            "title": created.title,
        }
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}

async def update_item_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Validate args & existence; update item."""
    try:
        data = _UpdateArgs(**args)
        item = crud.get_item(data.id)
        if not item:
            raise ValueError("item not found")
        update_data = data.model_dump(exclude={"id"}, exclude_none=True)
        if "parent_id" in update_data:
            new_parent_id = update_data["parent_id"]
            if new_parent_id is not None:
                new_parent = crud.get_item(new_parent_id)
                if not new_parent or new_parent.project_id != item.project_id:
                    raise ValueError("invalid parent_id")
                allowed = _ALLOWED_PARENT.get(item.type, [])
                if new_parent.type not in allowed or new_parent.id == item.id:
                    raise ValueError("invalid hierarchy")
                # detect cycles
                current = new_parent
                while current.parent_id is not None:
                    if current.parent_id == item.id:
                        raise ValueError("cycle detected")
                    current = crud.get_item(current.parent_id)
                    if current is None:
                        break
        updated = crud.update_item(data.id, BacklogItemUpdate(**update_data))
        return {
            "ok": True,
            "item_id": updated.id,
            "updated_fields": update_data,
        }
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}

async def find_item_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search items by fuzzy match in title."""
    try:
        data = _FindArgs(**args)
        items = crud.get_items(data.project_id, type=data.type)
        q = data.query.lower()
        matches = [
            {"id": it.id, "title": it.title, "type": it.type}
            for it in items
            if q in it.title.lower()
        ]
        return {"ok": True, "matches": matches}
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}

HANDLERS: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {
    "create_item": create_item_tool,
    "update_item": update_item_tool,
    "find_item": find_item_tool,
}
