"""Structured tool specifications exposed to LLMs."""

from typing import Optional, Literal, List, Dict

from pydantic import BaseModel, Field

try:  # LangChain 0.2.x
    from langchain.tools import StructuredTool
except Exception:  # pragma: no cover - fallback for older versions
    from langchain_core.tools import StructuredTool


# --- Pydantic v2 arg schemas ---
class CreateItemArgs(BaseModel):
    type: Literal["Epic", "Capability", "Feature", "US", "UC"]
    title: str
    project_id: int
    parent_id: Optional[int] = None
    description: Optional[str] = None


class UpdateItemArgs(BaseModel):
    id: int
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    parent_id: Optional[int] = None


class FindItemArgs(BaseModel):
    project_id: int
    type: Optional[Literal["Epic", "Capability", "Feature", "US", "UC"]] = None
    query: Optional[str] = None
    limit: int = 20


class GetItemArgs(BaseModel):
    id: Optional[int] = None
    type: Optional[Literal["Epic", "Capability", "Feature", "US", "UC"]] = None
    title: Optional[str] = None
    project_id: Optional[int] = None


class ListItemsArgs(BaseModel):
    project_id: int
    type: Optional[Literal["Epic", "Capability", "Feature", "US", "UC"]] = None
    query: Optional[str] = None
    limit: int = 100
    offset: int = 0


class DeleteItemArgs(BaseModel):
    id: int


class MoveItemArgs(BaseModel):
    id: int
    new_parent_id: int


class SummarizeProjectArgs(BaseModel):
    project_id: int
    depth: int = 3


class BulkCreateFeaturesArgs(BaseModel):
    project_id: int
    parent_id: int
    items: List[Dict[str, Optional[str]]] = Field(
        ..., description='List of {"title": str, "description": Optional[str]}'
    )


def _noop(**kwargs) -> str:  # jamais exécuté
    return "noop"


# --- Déclarations des tools (BaseTool) ---
create_item_decl = StructuredTool.from_function(
    name="create_item",
    description="Create a backlog item (Epic/Capability/Feature/US/UC). Avoid duplicates under same parent.",
    func=_noop,
    args_schema=CreateItemArgs,
)
update_item_decl = StructuredTool.from_function(
    name="update_item",
    description="Update fields of an existing item by ID.",
    func=_noop,
    args_schema=UpdateItemArgs,
)
find_item_decl = StructuredTool.from_function(
    name="find_item",
    description="Find items by project/type/query for disambiguation.",
    func=_noop,
    args_schema=FindItemArgs,
)
get_item_decl = StructuredTool.from_function(
    name="get_item",
    description="Get a single item by ID or by (type,title,project_id).",
    func=_noop,
    args_schema=GetItemArgs,
)
list_items_decl = StructuredTool.from_function(
    name="list_items",
    description="List items in a project; filter by type/query.",
    func=_noop,
    args_schema=ListItemsArgs,
)
delete_item_decl = StructuredTool.from_function(
    name="delete_item",
    description="Delete an item and its descendants.",
    func=_noop,
    args_schema=DeleteItemArgs,
)
move_item_decl = StructuredTool.from_function(
    name="move_item",
    description="Reparent an item (hierarchy enforced).",
    func=_noop,
    args_schema=MoveItemArgs,
)
summarize_project_decl = StructuredTool.from_function(
    name="summarize_project",
    description="Summarize the project tree and counts.",
    func=_noop,
    args_schema=SummarizeProjectArgs,
)
bulk_create_features_decl = StructuredTool.from_function(
    name="bulk_create_features",
    description="Create multiple Features under a parent; skip duplicates.",
    func=_noop,
    args_schema=BulkCreateFeaturesArgs,
)


TOOLS: List[StructuredTool] = [
    create_item_decl,
    update_item_decl,
    find_item_decl,
    get_item_decl,
    list_items_decl,
    delete_item_decl,
    move_item_decl,
    summarize_project_decl,
    bulk_create_features_decl,
]


# --- Handlers réels (exécution serveur) ---
from .handlers import (  # noqa: E402
    create_item_tool,
    update_item_tool,
    find_item_tool,
    get_item_tool,
    list_items_tool,
    delete_item_tool,
    move_item_tool,
    summarize_project_tool,
    bulk_create_features_tool,
)


HANDLERS = {
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

