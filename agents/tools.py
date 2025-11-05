from typing import Optional, Literal, List, Any, Union
from pydantic import BaseModel, ValidationError, Field, model_validator
import logging
import os
try:
    from langchain.tools import StructuredTool
except Exception:  # pragma: no cover - fallback for older versions
    from langchain_core.tools import StructuredTool

from orchestrator import crud
from orchestrator import stream  # assume stream.register/publish/close exist
import json
import asyncio
from datetime import datetime, date
from enum import Enum

from agents.tools_context import get_current_run_id
from agents.schemas import FeatureInput
from agents.generators.generate_full_tree import generate_full_tree_v1
from agents.generators.generate_full_tree_v2 import generate_full_tree_v2

logger = logging.getLogger(__name__)

# Default timeout for tool handlers in seconds. Can be overridden with the
# TOOL_TIMEOUT environment variable. Uses a generous default to avoid premature
# timeouts for LLM-backed tools.
try:
    TOOL_TIMEOUT = float(os.getenv("TOOL_TIMEOUT", "60"))
    if TOOL_TIMEOUT <= 0:
        raise ValueError
except ValueError:
    TOOL_TIMEOUT = 60.0

# ---------- Schemas Pydantic v2 ----------
class CreateItemArgs(BaseModel):
    type: Literal["Epic","Capability","Feature","US","UC"]
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
    type: Optional[Literal["Epic","Capability","Feature","US","UC"]] = None
    query: Optional[str] = None
    limit: int = 20

class GetItemArgs(BaseModel):
    id: Optional[int] = None
    type: Optional[Literal["Epic","Capability","Feature","US","UC"]] = None
    title: Optional[str] = None
    project_id: Optional[int] = None

class ListItemsArgs(BaseModel):
    project_id: int
    type: Optional[Literal["Epic","Capability","Feature","US","UC"]] = None
    query: Optional[str] = None
    limit: int = 100
    offset: int = 0

class DeleteItemArgs(BaseModel):
    id: int
    project_id: int
    type: Literal["Epic", "Capability", "Feature", "US", "UC"]
    reason: str
    explicit_confirm: bool = False

class MoveItemArgs(BaseModel):
    id: int
    new_parent_id: int

class SummarizeProjectArgs(BaseModel):
    project_id: int
    depth: int = 3

class BulkFeatureItem(BaseModel):
    title: str
    description: str | None = None
    acceptance_criteria: Union[str, List[str]] | None = None


class BulkCreateFeaturesArgs(BaseModel):
    project_id: int
    parent_id: int
    items: List[BulkFeatureItem]

    @model_validator(mode="after")
    def _normalize_acceptance_criteria(self):
        for item in self.items:
            ac = item.acceptance_criteria
            if ac is None:
                item.acceptance_criteria = ""
            elif isinstance(ac, list):
                cleaned = [str(x).strip() for x in ac if str(x).strip()]
                item.acceptance_criteria = "- " + "\n- ".join(cleaned) if cleaned else ""
            else:
                item.acceptance_criteria = str(ac).strip()
        return self

class ListDocsArgs(BaseModel):
    project_id: int

class SearchDocsArgs(BaseModel):
    project_id: int
    query: str

class GetDocArgs(BaseModel):
    doc_id: int

class DraftFeaturesArgs(BaseModel):
    project_id: int
    doc_query: str
    k: int = 6  # number of features to draft

class GenerateItemsArgs(BaseModel):
    project_id: int = Field(..., description="Project ID")
    parent_id: int = Field(..., description="Parent item ID")
    target_type: Literal["Feature", "US", "UC"]
    n: int | None = Field(6, description="How many items to generate (3..10)")


class GenerateFullTreeArgs(BaseModel):
    project_id: int
    theme: str | None = "e-commerce"


class GenerateFullTreeV2Args(BaseModel):
    project_id: int
    theme: str | None = "e-commerce"
    n_epics: int = 6
    n_features: int = 6
    n_us: int = 3
    n_uc: int = 2
    dry_run: bool = False

# ---------- HANDLERS réels ----------
from .handlers import (  # noqa: E402 - handlers import requires models above
    create_item_tool,
    update_item_tool,
    find_item_tool,
    get_item_tool,
    list_items_tool,
    delete_item_tool,
    move_item_tool,
    summarize_project_tool,
    bulk_create_features_tool,
    list_documents_handler,
    search_documents_handler,
    get_document_handler,
    draft_features_from_matches_handler,
    generate_items_from_parent_handler,
)

def _jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, BaseModel):
        return _jsonable(obj.model_dump())
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(v) for v in list(obj)]
    return str(obj)


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        sanitized: Dict[str, Any] = {}
        for k, v in obj.items():
            key_str = str(k)
            lowered = key_str.lower()
            if "key" in lowered or "secret" in lowered:
                continue
            sanitized[key_str] = _sanitize(v)
        return sanitized
    if isinstance(obj, (list, tuple, set)):
        return [_sanitize(v) for v in list(obj)]
    return _jsonable(obj)

# Chaque tool wrapper reçoit **run_id** dans le kwargs (injecté par l’agent, voir plus bas)
async def _exec(name: str, run_id: str, args: dict):
    logger.info("Executing tool '%s' with args: %s (run_id: %s)", name, args, run_id)
    safe_args = _sanitize(args or {})
    serialized_request = json.dumps({"name": name, "args": safe_args})
    crud.record_run_step(run_id, f"tool:{name}:request", serialized_request, broadcast=False)
    stream.publish(run_id, {"node": f"tool:{name}:request", "args": safe_args})
    
    handler = HANDLERS.get(name)
    if not handler:
        error_msg = f"No handler found for tool '{name}'"
        logger.error(error_msg)
        return json.dumps({"ok": False, "error": error_msg})
    
    try:
        logger.debug("Calling handler for tool '%s'", name)
        res = await asyncio.wait_for(handler(args), timeout=TOOL_TIMEOUT)
        logger.debug("Tool '%s' returned: %s", name, res)
    except ValidationError as ve:
        logger.error("Tool '%s' validation error: %s", name, ve)
        hint = {
            "ok": False,
            "error": "VALIDATION_ERROR",
            "tool": name,
            "message": str(ve),
            "expected": "For bulk_create_features you MUST provide 'items': [...]. See planner guidance.",
        }
        crud.record_run_step(run_id, f"tool:{name}:validation_error", json.dumps(_sanitize(hint)), broadcast=False)
        stream.publish(run_id, {"node": f"tool:{name}:validation_error", **hint})
        return json.dumps(hint)
    except asyncio.TimeoutError:
        logger.error("Tool '%s' timed out", name)
        res = {"ok": False, "error": "timeout"}
    except Exception as e:
        logger.error("Tool '%s' failed with exception: %s", name, str(e), exc_info=True)
        res = {"ok": False, "error": f"Tool execution failed: {str(e)}"}
    
    data = {k: v for k, v in res.items() if k not in {"ok", "error"}}
    safe_res = _sanitize(data)
    response_payload = {"ok": res.get("ok"), "result": safe_res, "error": res.get("error")}
    crud.record_run_step(run_id, f"tool:{name}:response", json.dumps(response_payload), broadcast=False)
    stream.publish(run_id, {"node": f"tool:{name}:response", **response_payload})
    # Renvoie une **string** (LC attend du texte des tools)
    result_json = json.dumps(_sanitize(res))
    logger.info("Tool '%s' execution completed, returning: %s", name, result_json)
    return result_json

# Déclarer des StructuredTool ASYNC (args_schema = Pydantic v2)
def _mk_tool(name: str, desc: str, schema: type[BaseModel]):
    async def _tool(**kwargs):
        logger.debug("Tool '%s' called with kwargs: %s", name, kwargs)
        run_id = kwargs.pop("run_id", None) or get_current_run_id()
        if not run_id:
            logger.warning("No run_id provided for tool '%s', using 'unknown'", name)
            run_id = "unknown"
        logger.debug("Tool '%s' using run_id: %s", name, run_id)
        return await _exec(name, run_id, kwargs)
    
    tool = StructuredTool.from_function(
        name=name,
        description=desc,
        coroutine=_tool,      # <- coroutine async
        args_schema=schema,
    )
    logger.info("Created tool '%s' with schema: %s", name, schema.__name__)
    
    # Log tool schema details for debugging
    try:
        schema_dict = schema.model_json_schema()
        logger.debug("Tool '%s' schema details: %s", name, schema_dict)
    except Exception as e:
        logger.warning("Could not serialize schema for tool '%s': %s", name, e)
        
    return tool

TOOLS = [
    _mk_tool("create_item", "Create a backlog item (Epic/Capability/Feature/US/UC). Avoid duplicates under the same parent.", CreateItemArgs),
    _mk_tool("update_item", "Update fields of an existing item by ID.", UpdateItemArgs),
    _mk_tool("find_item", "Find items by project/type/query for disambiguation.", FindItemArgs),
    _mk_tool("get_item", "Get a single item by ID or by (type,title,project_id).", GetItemArgs),
    _mk_tool("list_items", "List items within a project, optionally filter by type/query.", ListItemsArgs),
    _mk_tool("delete_item", "Delete an item and its descendants.", DeleteItemArgs),
    _mk_tool("move_item", "Reparent an item (hierarchy enforced).", MoveItemArgs),
    _mk_tool("summarize_project", "Summarize the project tree and counts.", SummarizeProjectArgs),
    _mk_tool("bulk_create_features", "Create multiple Features under a parent; skip duplicates.", BulkCreateFeaturesArgs),
    _mk_tool(
        "generate_items_from_parent",
        "Generate backlog items (Feature, US, or UC) under a parent item.",
        GenerateItemsArgs,
    ),
    _mk_tool("list_documents", "List documents in the project.", ListDocsArgs),
    _mk_tool("search_documents", "Search relevant passages in project documents.", SearchDocsArgs),
    _mk_tool("get_document", "Get full text content of a document by ID.", GetDocArgs),
    _mk_tool(
        "draft_features_from_matches",
        "Infer and create Feature backlog items from project documents. Returns {items:[{id,title}]}.",
        DraftFeaturesArgs,
    ),
    _mk_tool(
        "generate_full_tree_v1",
        "Créer une arborescence complète (Épics → Features → User Stories) pour un projet e-commerce.",
        GenerateFullTreeArgs,
    ),
    _mk_tool(
        "generate_full_tree_v2",
        "Créer/compléter l'arborescence e-commerce (Epic → Feature → US → UC) avec quotas configurables.",
        GenerateFullTreeV2Args,
    ),
]

# On conserve HANDLERS exporté si utilisé ailleurs
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
    "list_documents": list_documents_handler,
    "search_documents": search_documents_handler,
    "get_document": get_document_handler,
    "draft_features_from_matches": draft_features_from_matches_handler,
    "generate_items_from_parent": generate_items_from_parent_handler,
    "generate_full_tree_v1": generate_full_tree_v1,
    "generate_full_tree_v2": generate_full_tree_v2,
}
