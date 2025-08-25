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
TOOL_SYSTEM_PROMPT = """
You are an assistant that MANAGES a product backlog using the provided TOOLS.
Rules (must follow):
- When a user asks to create/update/delete/move/list/get/summarize items, you MUST call a TOOL. Do NOT answer with plain text only.
- NEVER invent IDs or fields.
- When an item is referenced by text (title/type), FIRST disambiguate using list_items or get_item before update/delete/move.
- If multiple candidates exist, ask exactly ONE short clarification question and then STOP.
- Avoid duplicates: before create, check existence with list_items.
- Keep ≤ 10 tool calls per objective. If you reach the limit, stop with a brief explanation.
- Final answer should be concise. After tool calls, summarize what changed and list affected item IDs.
- Do NOT return any placeholder like 'placeholder' or 'stub'. If critical info is missing (e.g., project_id), ask one question and stop.
"""
