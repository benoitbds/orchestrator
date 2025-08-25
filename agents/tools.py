"""Structured tool specifications exposed to LLMs."""

from typing import Literal, Optional, List

from langchain_core.tools import StructuredTool
from langchain_core.pydantic_v1 import BaseModel, Field

from .handlers import (
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


# ==== Schemas d'arguments ====
class CreateItemArgs(BaseModel):
    type: Literal["Epic", "Capability", "Feature", "US", "UC"] = Field(
        ..., description="Item type"
    )
    title: str = Field(..., description="Item title")
    project_id: int = Field(..., description="Project ID")
    parent_id: Optional[int] = Field(None, description="Parent item ID if any")
    description: Optional[str] = Field(None, description="Optional description")


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
    items: List[dict] = Field(
        ..., description='List of {"title": str, "description": Optional[str]}'
    )


# ==== Déclarations de tools (pour function-calling uniquement) ====
# La fonction lambda n'est jamais exécutée (on utilise HANDLERS côté serveur).
create_item_lc = StructuredTool.from_function(
    name="create_item",
    description="Create a backlog item (Epic/Capability/Feature/US/UC). Avoid duplicates under the same parent.",
    func=lambda **kwargs: "noop",
    args_schema=CreateItemArgs,
)
update_item_lc = StructuredTool.from_function(
    name="update_item",
    description="Update fields of an existing item by ID.",
    func=lambda **kwargs: "noop",
    args_schema=UpdateItemArgs,
)
find_item_lc = StructuredTool.from_function(
    name="find_item",
    description="Find items by project/type/query for disambiguation.",
    func=lambda **kwargs: "noop",
    args_schema=FindItemArgs,
)
get_item_lc = StructuredTool.from_function(
    name="get_item",
    description="Get a single item by ID or by (type,title,project_id).",
    func=lambda **kwargs: "noop",
    args_schema=GetItemArgs,
)
list_items_lc = StructuredTool.from_function(
    name="list_items",
    description="List items within a project, optionally filter by type/query.",
    func=lambda **kwargs: "noop",
    args_schema=ListItemsArgs,
)
delete_item_lc = StructuredTool.from_function(
    name="delete_item",
    description="Delete an item (and descendants).",
    func=lambda **kwargs: "noop",
    args_schema=DeleteItemArgs,
)
move_item_lc = StructuredTool.from_function(
    name="move_item",
    description="Reparent an item to a new parent (hierarchy rules enforced).",
    func=lambda **kwargs: "noop",
    args_schema=MoveItemArgs,
)
summarize_project_lc = StructuredTool.from_function(
    name="summarize_project",
    description="Summarize the project tree (counts and structure).",
    func=lambda **kwargs: "noop",
    args_schema=SummarizeProjectArgs,
)
bulk_create_features_lc = StructuredTool.from_function(
    name="bulk_create_features",
    description="Create multiple Features under a given parent, skipping duplicates.",
    func=lambda **kwargs: "noop",
    args_schema=BulkCreateFeaturesArgs,
)


# ==== Liste des tools exposés à LangChain ====
TOOLS = [
    create_item_lc,
    update_item_lc,
    find_item_lc,
    get_item_lc,
    list_items_lc,
    delete_item_lc,
    move_item_lc,
    summarize_project_lc,
    bulk_create_features_lc,
]


# ==== HANDLERS réels (exécutés par notre boucle outils) ====
# (ce mapping existait déjà chez toi)
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

