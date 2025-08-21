"""LLM tool specifications and handlers for backlog management."""
from __future__ import annotations

from typing import Any, Dict, Callable, Awaitable

from pydantic import BaseModel, ValidationError, field_validator

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

class ParentRef(BaseModel):
    """Reference to a parent item by type and title."""

    type: str
    title: str


class _CreateArgs(BaseModel):
    """Arguments accepted by ``create_item_tool``.

    ``parent`` is resolved by title/type; ``parent_id`` is kept for backward
    compatibility with existing tests/tools.
    """

    title: str
    type: str
    project_id: int
    description: str | None = None
    parent_id: int | None = None
    parent: ParentRef | None = None

    @field_validator("type")
    @classmethod
    def _normalise_type(cls, v: str) -> str:
        return v.upper() if v.lower() in {"us", "uc"} else v.capitalize()

class LookupRef(BaseModel):
    """Lookup reference used when updating without explicit id."""

    type: str
    title: str
    project_id: int

    @field_validator("type")
    @classmethod
    def _normalise_type(cls, v: str) -> str:
        return v.upper() if v.lower() in {"us", "uc"} else v.capitalize()


class UpdateFields(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    parent_id: int | None = None


class _UpdateArgs(BaseModel):
    id: int | None = None
    lookup: LookupRef | None = None
    fields: UpdateFields

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
    """Validate args and create a backlog item.

    ``parent`` can be provided instead of ``parent_id`` and will be resolved by
    title and type within the given project.  When multiple matches are found,
    an ``parent_ambiguous`` error is returned so the caller can clarify.
    """

    try:
        data = _CreateArgs(**args)
        parent_id = data.parent_id
        # Resolve parent if given as reference
        if data.parent is not None:
            items = crud.get_items(data.project_id, type=data.parent.type)
            matches = [
                it for it in items if it.title.lower() == data.parent.title.lower()
            ]
            if not matches:
                return {"ok": False, "error": "parent_not_found"}
            if len(matches) > 1:
                return {"ok": False, "error": "parent_ambiguous"}
            parent_id = matches[0].id

        if parent_id is not None:
            parent = crud.get_item(parent_id)
            if not parent or parent.project_id != data.project_id:
                raise ValueError("invalid parent_id")
            allowed = _ALLOWED_PARENT.get(data.type, [])
            if parent.type not in allowed:
                raise ValueError("invalid hierarchy")

        Model = _MODEL_MAP[data.type]
        item = Model(
            title=data.title,
            description=data.description or "",
            project_id=data.project_id,
            parent_id=parent_id,
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
    """Validate args & existence; update item.

    Supports targeting an item either by explicit ``id`` or by a lookup
    (``type`` + ``title`` + ``project_id``).  Updates are passed through to the
    CRUD layer after validating hierarchy rules.
    """

    try:
        # Backward compatibility: allow id/fields at top-level
        if "fields" not in args:
            lookup = None
            if args.get("id") is None and {
                "type",
                "title",
                "project_id",
            }.issubset(args):
                lookup = {
                    "type": args["type"],
                    "title": args["title"],
                    "project_id": args["project_id"],
                }
                fields = {
                    k: v
                    for k, v in args.items()
                    if k not in {"id", "type", "title", "project_id", "lookup"}
                }
            else:
                fields = {
                    k: v
                    for k, v in args.items()
                    if k not in {"id", "type", "project_id", "lookup"}
                }
            args = {"id": args.get("id"), "lookup": lookup, "fields": fields}

        data = _UpdateArgs(**args)

        item_id = data.id
        if item_id is None:
            # Resolve via lookup
            items = crud.get_items(
                data.lookup.project_id, type=data.lookup.type
            )
            matches = [
                it
                for it in items
                if it.title.lower() == data.lookup.title.lower()
            ]
            if not matches:
                return {"ok": False, "error": "item_not_found"}
            if len(matches) > 1:
                return {"ok": False, "error": "item_ambiguous"}
            item_id = matches[0].id

        item = crud.get_item(item_id)
        if not item:
            raise ValueError("item not found")

        update_data = data.fields.model_dump(exclude_none=True)

        if "parent_id" in update_data:
            new_parent_id = update_data["parent_id"]
            if new_parent_id is not None:
                new_parent = crud.get_item(new_parent_id)
                if not new_parent or new_parent.project_id != item.project_id:
                    raise ValueError("invalid parent_id")
                allowed = _ALLOWED_PARENT.get(item.type, [])
                if new_parent.type not in allowed or new_parent.id == item.id:
                    raise ValueError("invalid hierarchy")
                current = new_parent
                while current.parent_id is not None:
                    if current.parent_id == item_id:
                        raise ValueError("cycle detected")
                    current = crud.get_item(current.parent_id)
                    if current is None:
                        break

        if "status" in update_data and item.type in {"US", "UC"}:
            if update_data["status"] not in {"Todo", "Doing", "Done"}:
                raise ValueError("invalid status")
        elif "status" in update_data and item.type not in {"US", "UC"}:
            raise ValueError("invalid status")

        updated = crud.update_item(item_id, BacklogItemUpdate(**update_data))
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
