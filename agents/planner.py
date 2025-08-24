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
    "You manage a product backlog using provided tools. NEVER invent IDs or fields. "
    "When referencing an item by text (title/type), ALWAYS disambiguate using list_items or get_item FIRST. "
    "If multiple matches exist, ask one short clarifying question or pick the best match only after calling list_items and explain the choice. "
    "Prefer concise answers. After tool calls, summarize what changed: list created/updated/deleted items with IDs. "
    "If critical info is missing (e.g., project_id), ask exactly one clarifying question, then stop. Do NOT proceed without required info. "
    "Keep the loop under N tool calls (configurable). If reached, stop and return an intelligible message. "
    "Do not create duplicates under the same parent. Use list_items to check existence first for creation."
)
