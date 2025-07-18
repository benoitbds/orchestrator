# orchestrator/core_loop.py
from __future__ import annotations
import sqlite3, datetime as dt, json
from typing import List, Optional, Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ConfigDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from agents.planner import make_plan
from agents.executor import run_python
from agents.writer import render_exec
from agents.schemas import ExecResult, Plan, RenderResult
import threading

load_dotenv()

# ---------- Mini-mémoire SQLite ----------
class Memory:
    def __init__(self, db_path: str = "orchestrator.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS trace "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, role TEXT, content TEXT)"
        )

    def add(self, role: str, content: str):
        with self.lock:
            from datetime import datetime, timezone
            ts = datetime.now(timezone.utc).isoformat()
            self.conn.execute(
                "INSERT INTO trace (ts, role, content) VALUES (?, ?, ?)",
                (ts, role, content),
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
    plan: Optional[Plan] = None
    exec_result: Optional[dict] = None
    render: Optional[str] = None
    result: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)  # <- clé

# ---------- LangGraph nodes ----------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

def planner(state: LoopState) -> dict:
    plan = make_plan(state.objective)
    state.mem_obj.add("agent-planner", json.dumps(plan.model_dump()))
    return {"plan": plan}

def executor(state: LoopState) -> dict:
    #  ici on exécute juste un “print objective” pour démo
    first_step = state.plan.steps[0]
    code = f'print("{first_step.title}")'
    exec_res = run_python(code)
    snippet = (exec_res.stdout or exec_res.stderr)[:512]
    state.mem_obj.add("agent-executor", snippet)
    return {"exec_result": exec_res.model_dump()}

def writer(state: LoopState) -> dict:
    er = ExecResult(**state.exec_result)
    render = render_exec(er, state.objective)
    state.mem_obj.add("agent-writer", render.summary)
    state.mem_obj.add("assistant", render.summary)
    return {
       "render": render.model_dump(),
       "result": render.summary
    }

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
