from typing import Any
import json
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from .schemas import Plan

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
"""
