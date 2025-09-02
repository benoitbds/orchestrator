from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, ValidationError
import logging
try:
    from langchain.tools import StructuredTool
except Exception:  # pragma: no cover - fallback for older versions
    from langchain_core.tools import StructuredTool

from orchestrator import crud
from orchestrator import stream  # assume stream.register/publish/close exist
import json
import asyncio

logger = logging.getLogger(__name__)

# Hook global (très simple): si run_id absent des kwargs, essaie de le lire depuis contexte global
_CURRENT_RUN_ID: str | None = None


def set_current_run(run_id: str):  # appelé par run_chat_tools avant l'exec
    global _CURRENT_RUN_ID
    _CURRENT_RUN_ID = run_id
    logger.info("Set current run ID: %s", run_id)

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

class MoveItemArgs(BaseModel):
    id: int
    new_parent_id: int

class SummarizeProjectArgs(BaseModel):
    project_id: int
    depth: int = 3

class BulkCreateFeaturesArgs(BaseModel):
    project_id: int
    parent_id: int
    items: List[Dict[str, Optional[str]]]

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
)

def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k,v in obj.items() if "key" not in k.lower() and "secret" not in k.lower()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj

# Chaque tool wrapper reçoit **run_id** dans le kwargs (injecté par l’agent, voir plus bas)
async def _exec(name: str, run_id: str, args: dict):
    logger.info("Executing tool '%s' with args: %s (run_id: %s)", name, args, run_id)
    safe_args = _sanitize(args or {})
    crud.record_run_step(run_id, f"tool:{name}:request", json.dumps({"name": name, "args": safe_args}), broadcast=False)
    stream.publish(run_id, {"node": f"tool:{name}:request", "args": safe_args})
    
    handler = HANDLERS.get(name)
    if not handler:
        error_msg = f"No handler found for tool '{name}'"
        logger.error(error_msg)
        return json.dumps({"ok": False, "error": error_msg})
    
    try:
        logger.debug("Calling handler for tool '%s'", name)
        res = await asyncio.wait_for(handler(args), timeout=12)
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
        crud.record_run_step(run_id, f"tool:{name}:validation_error", json.dumps(hint), broadcast=False)
        stream.publish(run_id, {"node": f"tool:{name}:validation_error", **hint})
        return json.dumps(hint)
    except asyncio.TimeoutError:
        logger.error("Tool '%s' timed out", name)
        res = {"ok": False, "error": "timeout"}
    except Exception as e:
        logger.error("Tool '%s' failed with exception: %s", name, str(e), exc_info=True)
        res = {"ok": False, "error": f"Tool execution failed: {str(e)}"}
    
    data = {k: v for k, v in res.items() if k not in {"ok","error"}}
    safe_res = _sanitize(data)
    crud.record_run_step(run_id, f"tool:{name}:response", json.dumps({"ok": res.get("ok"), "result": safe_res, "error": res.get("error")}), broadcast=False)
    stream.publish(run_id, {"node": f"tool:{name}:response", "ok": res.get("ok"), "result": safe_res, "error": res.get("error")})
    # Renvoie une **string** (LC attend du texte des tools)
    result_json = json.dumps(res)
    logger.info("Tool '%s' execution completed, returning: %s", name, result_json)
    return result_json

# Déclarer des StructuredTool ASYNC (args_schema = Pydantic v2)
def _mk_tool(name: str, desc: str, schema: type[BaseModel]):
    async def _tool(**kwargs):
        logger.debug("Tool '%s' called with kwargs: %s", name, kwargs)
        run_id = kwargs.pop("run_id", None) or _CURRENT_RUN_ID
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
    _mk_tool("list_documents", "List documents in the project.", ListDocsArgs),
    _mk_tool("search_documents", "Search relevant passages in project documents.", SearchDocsArgs),
    _mk_tool("get_document", "Get full text content of a document by ID.", GetDocArgs),
    _mk_tool(
        "draft_features_from_matches",
        "Infer and create Feature backlog items from project documents. Returns {items:[{id,title}]}.",
        DraftFeaturesArgs,
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
}
