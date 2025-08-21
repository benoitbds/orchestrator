# orchestrator/core_loop.py
from __future__ import annotations
import sqlite3
import json
from typing import List, Optional, Any
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ConfigDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from agents.planner import make_plan
from agents.schemas import ExecResult, Plan
import threading
from orchestrator import crud

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
    """State shared across LangGraph nodes."""

    objective: str
    project_id: int | None = None
    run_id: str
    mem_obj: Memory
    memory: List[Any] = Field(default_factory=list)
    plan: Optional[Plan] = None
    exec_result: Optional[dict] = None
    render: Optional[str] = None
    result: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)  # <- clé

# ---------- LangGraph nodes ----------
llm_step = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

def planner(state: LoopState) -> dict:
    """Generate a plan and record the step."""
    plan = make_plan(state.objective)
    payload = json.dumps(plan.model_dump())
    state.mem_obj.add("agent-planner", payload)
    crud.record_run_step(state.run_id, "plan", payload)
    return {"plan": plan}


def executor(state: LoopState) -> dict:
    """Execute each plan step sequentially and record outputs."""
    outputs = []
    for step in state.plan.steps:
        prompt = (
            f"Objectif : {state.objective}\n"
            f"Historique :\n{''.join(outputs) if outputs else '—'}\n\n"
            f"== Étape {step.id}: {step.title} ==\n{step.description}\n"
            "Réalise cette étape et renvoie UNIQUEMENT le résultat brut."
        )
        rsp = llm_step.invoke(prompt).content.strip()
        outputs.append(f"### {step.title}\n{rsp}\n")
        crud.record_run_step(
            state.run_id,
            "execute",
            json.dumps({"title": step.title, "result": rsp}),
        )

    exec_res = ExecResult(success=True, stdout="\n".join(outputs), stderr="")
    full_output = "\n".join(outputs)
    state.mem_obj.add("agent-executor", full_output)
    return {"exec_result": exec_res.model_dump()}


def writer(state: LoopState) -> dict:
    """Summarise execution results and record the final output."""
    er = ExecResult(**state.exec_result)

    html = (
        f"<h2>Résultat : {state.objective}</h2>\n"
        f"<pre><code>{er.stdout.strip()}</code></pre>"
    )
    summary = er.stdout.strip() if er.stdout.strip() else "Aucun résultat"

    render = {"html": html, "summary": summary, "artifacts": []}
    state.mem_obj.add("agent-writer", summary)
    state.mem_obj.add("assistant", summary)
    crud.record_run_step(state.run_id, "write", json.dumps(render))
    # mark run as finished with the final render
    crud.finish_run(state.run_id, render["html"], render["summary"])
    return {"render": render, "result": summary}

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
    run_id = str(uuid4())
    crud.create_run(run_id, objective, None)
    state = LoopState(objective=objective, mem_obj=mem, memory=mem.fetch(), run_id=run_id)
    result = graph.invoke(state)
    print("✅ Résultat complet :\n", result["render"]["html"])

if __name__ == "__main__":
    import typer
    typer.run(run)
