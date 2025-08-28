from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field
try:
    from langchain.tools import StructuredTool
except Exception:  # pragma: no cover - fallback for older versions
    from langchain_core.tools import StructuredTool

from orchestrator import crud
from orchestrator import stream  # assume stream.register/publish/close exist
import json
import asyncio

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

# ---------- HANDLERS réels ----------
from .handlers import (
    create_item_tool, update_item_tool, find_item_tool, get_item_tool, list_items_tool,
    delete_item_tool, move_item_tool, summarize_project_tool, bulk_create_features_tool,
)

def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k,v in obj.items() if "key" not in k.lower() and "secret" not in k.lower()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj

# Chaque tool wrapper reçoit **run_id** dans le kwargs (injecté par l’agent, voir plus bas)
async def _exec(name: str, run_id: str, args: dict):
    safe_args = _sanitize(args or {})
    crud.record_run_step(run_id, f"tool:{name}:request", json.dumps({"name": name, "args": safe_args}), broadcast=False)
    stream.publish(run_id, {"node": f"tool:{name}:request", "args": safe_args})
    handler = HANDLERS[name]
    try:
        res = await asyncio.wait_for(handler(args), timeout=12)
    except asyncio.TimeoutError:
        res = {"ok": False, "error": "timeout"}
    data = {k: v for k, v in res.items() if k not in {"ok","error"}}
    safe_res = _sanitize(data)
    crud.record_run_step(run_id, f"tool:{name}:response", json.dumps({"ok": res.get("ok"), "result": safe_res, "error": res.get("error")}), broadcast=False)
    stream.publish(run_id, {"node": f"tool:{name}:response", "ok": res.get("ok"), "result": safe_res, "error": res.get("error")})
    # Renvoie une **string** (LC attend du texte des tools)
    return json.dumps(res)

# Déclarer des StructuredTool ASYNC (args_schema = Pydantic v2)
def _mk_tool(name: str, desc: str, schema: type[BaseModel]):
    async def _tool(**kwargs):
        run_id = kwargs.pop("run_id")  # <- on l’injecte via l’agent
        return await _exec(name, run_id, kwargs)
    return StructuredTool.from_function(
        name=name,
        description=desc,
        coroutine=_tool,      # <- coroutine async
        args_schema=schema,
    )

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
}
