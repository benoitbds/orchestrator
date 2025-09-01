from typing import Any, Dict
import json
import os
from uuid import uuid4
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from orchestrator import crud, stream
from .schemas import Plan
from .tools import TOOLS

# Reference tools to ensure they're loaded for agent runs
_ = TOOLS

# Load environment variables
load_dotenv()

class PydanticOutputParser:
    def __init__(self, pydantic_object: Any):
        self.model = pydantic_object
    def get_format_instructions(self) -> str:
        return json.dumps(self.model.model_json_schema())
    def parse(self, text: str) -> Any:
        return self.model.model_validate_json(text)

llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4"), temperature=0.2)
parser = PydanticOutputParser(Plan)

def make_plan(objective: str) -> Plan:
    rsp = llm.invoke([{"role": "user", "content": objective}])
    return parser.parse(rsp.content)


# Prompt used by the tool-enabled chat executor
TOOL_SYSTEM_PROMPT = """
You are a backlog manager with access to TOOLS for managing functional items (Epics, Capabilities, Features, User Stories, Use Cases).

CRITICAL RULES (must follow):
- You MUST use tools for ALL create/update/delete/move/list/get/summarize operations. NEVER provide text-only responses for these actions.
- Always call the appropriate tool to perform the requested action.
- If you need information before acting, use list_items or get_item tools first.

WORKFLOW:
1. For ambiguous requests, use list_items to find existing items
2. For creation, check for duplicates first using list_items
3. For updates/deletes, use get_item to verify the item exists
4. Always use the exact item IDs returned by tools

CONSTRAINTS:
- NEVER invent IDs or make assumptions about data
- Project hierarchy: Epic → Capability → Feature → US → UC
- Keep tool calls ≤ 10 per conversation
- If critical info (project_id) is missing, ask ONE clarifying question then STOP
- Final response should be concise and include affected item IDs

Available tools: create_item, update_item, find_item, get_item, list_items, delete_item, move_item, summarize_project, bulk_create_features

You also have tools to manage project documents:
- list_documents(project_id): list all documents for the current project.
- search_documents(project_id, query): retrieve the most relevant passages from attached documents.
- get_document(doc_id): fetch the full text of a small document when needed.
Use these whenever the user mentions a PDF, requirements, 'cahier des charges', or asks for information likely contained in attached files. Prefer search_documents to avoid loading large texts.

When you want to create multiple Features at once you MUST call:
bulk_create_features(project_id: int, parent_id: int, items: FeatureInput[])

Where FeatureInput is an array of JSON objects with at least:
[
  {
    "title": "<clear feature title>",
    "description": "<1-3 sentences>",
    "type": "Feature",
    "acceptance_criteria": [
      "Given ... When ... Then ...",
      "Given ... When ... Then ..."
    ]
  },
  ...
]

Process:
1) Use search_documents(project_id, query) to find relevant excerpts.
2) Draft 3–7 Features synthesizing the excerpts (no duplicates).
3) Call bulk_create_features with the 'items' array (do NOT omit it).
4) Parent the features under 'parent_id' (Epic) provided by the user or selected item.
"""

async def run_objective(project_id: int, objective: str) -> Dict[str, Any]:
    """Execute a single objective using the agent tools."""
    
    # Import here to avoid circular dependency (core_loop imports this module)
    from orchestrator.core_loop import run_chat_tools
    
    # Use a temporary string run_id for the existing core_loop function
    temp_run_id = str(uuid4())
    try:
        await run_chat_tools(objective, project_id, temp_run_id)
        result = {"ok": True, "note": "Objective execution completed"}
    except Exception as e:
        result = {"ok": False, "error": str(e)}
    return result

