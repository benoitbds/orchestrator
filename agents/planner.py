# agents/planner.py
from dotenv import load_dotenv
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

from .schemas import Plan

load_dotenv()


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
parser = PydanticOutputParser(pydantic_object=Plan)

SYSTEM_PROMPT = (
    "Tu es un planificateur expert. "
    "Réponds STRICTEMENT en JSON conforme à ce schéma:\n"
    f"{parser.get_format_instructions()}"
)

def make_plan(objective: str) -> Plan:
    user_msg = (
        f"Objectif: {objective}\n"
        "Détaille un plan (3-6 étapes max) avec id, title, description, depends_on."
    )
    rsp = llm.invoke([{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": user_msg}])
    return parser.parse(rsp.content)
