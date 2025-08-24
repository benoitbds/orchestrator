from typing import Any
import json
from langchain_openai import ChatOpenAI
from .schemas import Plan

class PydanticOutputParser:
    def __init__(self, pydantic_object: Any):
        self.model = pydantic_object
    def get_format_instructions(self) -> str:
        return json.dumps(self.model.model_json_schema())
    def parse(self, text: str) -> Any:
        return self.model.model_validate_json(text)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
parser = PydanticOutputParser(Plan)

def make_plan(objective: str) -> Plan:
    rsp = llm.invoke([{"role": "user", "content": objective}])
    return parser.parse(rsp.content)


# Prompt used by the tool-enabled chat executor
TOOL_SYSTEM_PROMPT = (
    "You manage a product backlog via TOOLS. NEVER invent IDs or fields. "
    "When an item is referenced by text, FIRST disambiguate using list_items/get_item. "
    "If multiple candidates exist, ask ONE short clarification then stop. "
    "Prefer concise outputs. After tool calls, summarize created/updated/deleted items with IDs. "
    "Do NOT return a placeholder or 'stub'. If required info is missing (e.g., project_id), ask exactly one clarification and stop. "
    "Keep total tool calls ≤ 10. "
    "Avoid duplicates under the same parent (use list_items before create)."
)
