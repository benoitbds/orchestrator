from typing import Any, Dict
import json
import os
from uuid import uuid4
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from orchestrator import crud, stream
from orchestrator.prompt_loader import load_prompt
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
TOOL_SYSTEM_PROMPT = load_prompt("tool_system_prompt")

async def run_objective(project_id: int, objective: str) -> Dict[str, Any]:
    """Execute a single objective using the agent tools.

    A new run is created and its identifier is returned so that callers can
    later query progress or attach to the streaming API.
    """

    from orchestrator.core_loop import run_chat_tools

    run_id = str(uuid4())
    crud.create_run(run_id, objective, project_id)
    try:
        await run_chat_tools(objective, project_id, run_id)
        return {"ok": True, "run_id": run_id}
    except Exception as e:  # pragma: no cover - unexpected failures
        crud.finish_run(run_id, "", str(e), {})
        return {"ok": False, "run_id": run_id, "error": str(e)}

