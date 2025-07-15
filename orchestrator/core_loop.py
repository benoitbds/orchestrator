# orchestrator/core_loop.py
from __future__ import annotations
import sqlite3, datetime as dt, json
from typing import List, Optional, Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ConfigDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

load_dotenv()

# ---------- Mini-mémoire SQLite ----------
class Memory:
    def __init__(self, db_path: str = "orchestrator.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS trace "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, role TEXT, content TEXT)"
        )

    def add(self, role: str, content: str):
        self.conn.execute(
            "INSERT INTO trace (ts, role, content) VALUES (?, ?, ?)",
            (dt.datetime.utcnow().isoformat(), role, content),
        )
        self.conn.commit()

    def fetch(self, limit: int = 10) -> List[tuple[str, str]]:
        cur = self.conn.execute(
            "SELECT role, content FROM trace ORDER BY id DESC LIMIT ?", (limit,)
        )
        return list(reversed(cur.fetchall()))

# ---------- State schema (Pydantic) ----------
class LoopState(BaseModel):
    objective: str
    mem_obj: Memory
    memory: List[Any] = Field(default_factory=list)
    plan: Optional[List[str]] = None
    result: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)  # <- clé

# ---------- LangGraph nodes ----------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

def planner(state: LoopState) -> dict:
    prompt = (
        "Tu es un planificateur très concis.\n"
        f"Contexte récent: {state.memory}\n"
        f"Objectif: {state.objective}\n"
        "Propose un plan en 3-6 étapes, renvoie un JSON array d'étapes."
    )
    plan_raw = llm.invoke(prompt).content
    try:
        plan = json.loads(plan_raw)
    except json.JSONDecodeError:
        plan = [plan_raw]
    return {"plan": plan}

def executor(state: LoopState) -> dict:
    step = state.plan[0] if state.plan else state.objective
    result = llm.invoke(
        f"Exécute l'étape suivante : {step}\nRéponds en résumé."
    ).content
    return {"result": result}

def writer(state: LoopState) -> dict:
    state.mem_obj.add("assistant", state.result)
    return {}

# ---------- Build & compile graph ----------
def build_graph():
    sg = StateGraph(LoopState)
    sg.add_node("plan", planner)
    sg.add_node("execute", executor)
    sg.add_node("write", writer)

    sg.set_entry_point("plan")
    sg.add_edge("plan", "execute")
    sg.add_edge("execute", "write")
    sg.add_edge("write", END)
    return sg.compile()

graph = build_graph()

# ---------- CLI ----------
def run(objective: str):
    mem = Memory()
    state = LoopState(objective=objective, mem_obj=mem, memory=mem.fetch())
    result = graph.invoke(state)
    print("✅ Résultat :\n", result["result"])

if __name__ == "__main__":
    import typer
    typer.run(run)
