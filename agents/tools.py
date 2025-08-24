"""LLM tool specifications and handlers for backlog management."""
from __future__ import annotations

from typing import Any, Dict, Callable, Awaitable, List

from collections import Counter, defaultdict

from pydantic import BaseModel, ValidationError, field_validator, model_validator

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

get_item_spec = {
    "name": "get_item",
    "description": "Fetch a single item by id or by (type, title, project_id).",
    "parameters": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "type": {
                "type": "string",
                "enum": ["Epic", "Capability", "Feature", "US", "UC"],
            },
            "title": {"type": "string"},
            "project_id": {"type": "integer"},
        },
        "oneOf": [
            {"required": ["id"]},
            {"required": ["type", "title", "project_id"]},
        ],
    },
}

list_items_spec = {
    "name": "list_items",
    "description": "List items for a project with optional filters.",
    "parameters": {
        "type": "object",
        "properties": {
            "project_id": {"type": "integer"},
            "type": {
                "type": "string",
                "enum": ["Epic", "Capability", "Feature", "US", "UC"],
            },
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 100},
            "offset": {"type": "integer", "default": 0},
        },
        "required": ["project_id"],
    },
}

delete_item_spec = {
    "name": "delete_item",
    "description": "Delete an item and its descendants.",
    "parameters": {
        "type": "object",
        "properties": {"id": {"type": "integer"}},
        "required": ["id"],
    },
}

move_item_spec = {
    "name": "move_item",
    "description": "Reparent an item while enforcing hierarchy rules.",
    "parameters": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "new_parent_id": {"type": "integer"},
        },
        "required": ["id", "new_parent_id"],
    },
}

summarize_project_spec = {
    "name": "summarize_project",
    "description": "Generate a short textual summary of the project tree.",
    "parameters": {
        "type": "object",
        "properties": {
            "project_id": {"type": "integer"},
            "depth": {"type": "integer", "default": 3},
        },
        "required": ["project_id"],
    },
}

bulk_create_features_spec = {
    "name": "bulk_create_features",
    "description": "Create multiple features under an epic or capability.",
    "parameters": {
        "type": "object",
        "properties": {
            "project_id": {"type": "integer"},
            "parent_id": {"type": "integer"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["title"],
                },
            },
        },
        "required": ["project_id", "parent_id", "items"],
    },
}

TOOLS = [
    create_item_spec,
    update_item_spec,
    find_item_spec,
    get_item_spec,
    list_items_spec,
    delete_item_spec,
    move_item_spec,
    summarize_project_spec,
    bulk_create_features_spec,
]

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


class _GetArgs(BaseModel):
    id: int | None = None
    type: str | None = None
    title: str | None = None
    project_id: int | None = None

    @field_validator("type")
    @classmethod
    def _normalise_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.upper() if v.lower() in {"us", "uc"} else v.capitalize()

    @model_validator(mode="after")
    def _check_one_of(cls, data: "_GetArgs") -> "_GetArgs":
        if data.id is None and not all([data.type, data.title, data.project_id]):
            raise ValueError("id or (type,title,project_id) required")
        return data


class _ListArgs(BaseModel):
    project_id: int
    type: str | None = None
    query: str | None = None
    limit: int = 100
    offset: int = 0

    @field_validator("type")
    @classmethod
    def _normalise_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.upper() if v.lower() in {"us", "uc"} else v.capitalize()


class _DeleteArgs(BaseModel):
    id: int


class _MoveArgs(BaseModel):
    id: int
    new_parent_id: int


class _SummarizeArgs(BaseModel):
    project_id: int
    depth: int = 3


class _BulkFeature(BaseModel):
    title: str
    description: str | None = None


class _BulkCreateArgs(BaseModel):
    project_id: int
    parent_id: int
    items: List[_BulkFeature]

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


async def get_item_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch a single item by id or by lookup."""
    try:
        data = _GetArgs(**args)
        if data.id is not None:
            item = crud.get_item(data.id)
            if not item:
                return {"ok": False, "error": "item_not_found"}
        else:
            items = crud.get_items(data.project_id, type=data.type)
            matches = [
                it
                for it in items
                if it.title.lower() == data.title.lower()
            ]
            if not matches:
                return {"ok": False, "error": "item_not_found"}
            if len(matches) > 1:
                return {"ok": False, "error": "item_ambiguous"}
            item = matches[0]
        return {
            "ok": True,
            "result": {
                "id": item.id,
                "type": item.type,
                "title": item.title,
                "description": getattr(item, "description", ""),
                "status": getattr(item, "status", None),
                "parent_id": item.parent_id,
            },
        }
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}


async def list_items_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """List items for a project with optional filters."""
    try:
        data = _ListArgs(**args)
        items = crud.get_items(
            data.project_id, type=data.type, limit=data.limit, offset=data.offset
        )
        if data.query:
            q = data.query.lower()
            items = [it for it in items if q in it.title.lower()]
        result = [
            {
                "id": it.id,
                "type": it.type,
                "title": it.title,
                "parent_id": it.parent_id,
                "status": getattr(it, "status", None),
            }
            for it in items
        ]
        return {"ok": True, "result": result}
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}


async def delete_item_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete an item and its descendants."""
    try:
        data = _DeleteArgs(**args)
        item = crud.get_item(data.id)
        if not item:
            return {"ok": False, "error": "item_not_found"}
        deleted = crud.delete_item(data.id)
        return {"ok": True, "result": {"deleted": deleted}}
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}


async def move_item_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Reparent an item while enforcing hierarchy rules."""
    try:
        data = _MoveArgs(**args)
        item = crud.get_item(data.id)
        if not item:
            return {"ok": False, "error": "item_not_found"}
        new_parent = crud.get_item(data.new_parent_id)
        if not new_parent or new_parent.project_id != item.project_id:
            return {"ok": False, "error": "invalid_parent"}
        if new_parent.id == item.id:
            return {"ok": False, "error": "cycle_detected"}
        if item.parent_id == new_parent.id:
            return {
                "ok": True,
                "result": {
                    "id": item.id,
                    "type": item.type,
                    "title": item.title,
                    "parent_id": item.parent_id,
                    "status": getattr(item, "status", None),
                },
            }
        allowed = _ALLOWED_PARENT.get(item.type, [])
        if new_parent.type not in allowed:
            return {"ok": False, "error": "invalid_parent_type"}
        current = new_parent
        while current.parent_id is not None:
            if current.parent_id == item.id:
                return {"ok": False, "error": "cycle_detected"}
            current = crud.get_item(current.parent_id)
            if current is None:
                break
        updated = crud.update_item(item.id, BacklogItemUpdate(parent_id=new_parent.id))
        return {
            "ok": True,
            "result": {
                "id": updated.id,
                "type": updated.type,
                "title": updated.title,
                "parent_id": updated.parent_id,
                "status": getattr(updated, "status", None),
            },
        }
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}


async def summarize_project_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Summarise project structure and counts."""
    try:
        data = _SummarizeArgs(**args)
        items = crud.get_items(data.project_id, limit=1000)
        counts = Counter(it.type for it in items)
        children = defaultdict(list)
        for it in items:
            children[it.parent_id].append(it)

        def walk(parent_id: int | None, depth: int, level: int = 0) -> List[str]:
            lines: List[str] = []
            if depth <= 0:
                return lines
            for child in children.get(parent_id, []):
                lines.append("  " * level + f"{child.type}: {child.title}")
                lines.extend(walk(child.id, depth - 1, level + 1))
            return lines

        text = "\n".join(walk(None, data.depth)) or "(empty)"
        result = {
            "text": text,
            "counts": {t: counts.get(t, 0) for t in ["Epic", "Capability", "Feature", "US", "UC"]},
        }
        return {"ok": True, "result": result}
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}


async def bulk_create_features_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create multiple features under a parent item."""
    try:
        data = _BulkCreateArgs(**args)
        parent = crud.get_item(data.parent_id)
        if not parent or parent.project_id != data.project_id:
            return {"ok": False, "error": "invalid_parent"}
        if parent.type not in {"Epic", "Capability"}:
            return {"ok": False, "error": "invalid_parent_type"}
        existing = {
            it.title.lower()
            for it in crud.get_items(data.project_id, type="Feature", limit=1000)
            if it.parent_id == data.parent_id
        }
        created_ids: List[int] = []
        seen: set[str] = set()
        for item in data.items:
            title_key = item.title.lower()
            if title_key in existing or title_key in seen:
                continue
            feature = FeatureCreate(
                title=item.title,
                description=item.description or "",
                project_id=data.project_id,
                parent_id=data.parent_id,
            )
            created = crud.create_item(feature)
            created_ids.append(created.id)
            seen.add(title_key)
        return {"ok": True, "result": {"created_ids": created_ids}}
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}

HANDLERS: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {
    "create_item": create_item_tool,
    "update_item": update_item_tool,
    "find_item": find_item_tool,
    "get_item": get_item_tool,
    "list_items": list_items_tool,
    "delete_item": delete_item_tool,
    "move_item": move_item_tool,
    "summarize_project": summarize_project_tool,
    "bulk_create_features": bulk_create_features_tool,
}
