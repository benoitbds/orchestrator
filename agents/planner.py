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
You manage a product backlog using the provided TOOLS.

Hard rules (must follow):
- For any state-changing request (create/update/delete/move) and for list/get/summarize, you MUST call a TOOL. Do NOT answer with plain text only.
- For item creation, if the title is not in quotes, the word(s) following the item type should be used as the title. For example, 'create a feature test' implies a Feature with the title 'test'.
- NEVER invent IDs or fields.
- When an item is referenced by text (title/type), FIRST disambiguate via list_items/get_item. If multiple matches: ask exactly ONE short clarification, then STOP.
- Avoid duplicates: before create, check existence with list_items.
- Keep total tool calls ≤ 10. If reached, stop with a brief explanation.
- Final answer must be concise and list affected item IDs.
- Do NOT return placeholders like 'placeholder' or 'stub'. If critical info (e.g., project_id) is missing, ask one question then STOP.
"""
