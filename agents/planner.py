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
You are a backlog manager with access to TOOLS.

Rules (must follow):
- For create/update/delete/move/list/get/summarize requests, USE A TOOL. Do NOT answer with plain text only.
- NEVER invent IDs or fields.
- When an item is referenced by text (title/type), FIRST disambiguate using list_items or get_item. If multiple candidates exist, ask ONE short clarification, then STOP.
- Avoid duplicates: before create, check existence with list_items.
- Keep ≤ 10 tool calls. If reached, stop with a brief explanation.
- Final answer is concise and lists affected item IDs.
- Do NOT output placeholders like 'placeholder' or 'stub'. If critical info (e.g., project_id) is missing, ask one question then STOP.
"""
