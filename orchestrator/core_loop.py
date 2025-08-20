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
    objective: str
    project_id: int | None = None
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    mem_obj: Memory
    memory: List[Any] = Field(default_factory=list)
    plan: Optional[Plan] = None
    exec_result: Optional[dict] = None
    render: Optional[str] = None
    result: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)  # <- clé

# ---------- LangGraph nodes ----------
llm_step = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
def track_step(name: str):
    def decorator(fn):
        def wrapped(state: LoopState):
            content = "success"
            try:
                return fn(state)
            except Exception as exc:
                content = f"error: {exc}"
                raise
            finally:
                crud.record_run_step(state.run_id, name, content)
        return wrapped
    return decorator

@track_step("plan")
def planner(state: LoopState) -> dict:
    plan = make_plan(state.objective)
    state.mem_obj.add("agent-planner", json.dumps(plan.model_dump()))
    return {"plan": plan}

@track_step("execute")
def executor(state: LoopState) -> dict:
    outputs = []          # garde la sortie de chaque étape
    for step in state.plan.steps:
        prompt = (
            f"Objectif : {state.objective}\n"
            f"Historique :\n{''.join(outputs) if outputs else '—'}\n\n"
            f"== Étape {step.id}: {step.title} ==\n{step.description}\n"
            "Réalise cette étape et renvoie UNIQUEMENT le résultat brut."
        )
        rsp = llm_step.invoke(prompt).content.strip()
        outputs.append(f"### {step.title}\n{rsp}\n")

    exec_res = ExecResult(success=True, stdout="\n".join(outputs), stderr="")
    # Sauvegarder l'ensemble du message au lieu de seulement les 256 premiers caractères de la dernière sortie
    full_output = "\n".join(outputs)
    state.mem_obj.add("agent-executor", full_output)
    return {"exec_result": exec_res.model_dump()}

@track_step("write")
def writer(state: LoopState) -> dict:
    er = ExecResult(**state.exec_result)

    # HTML complet + résumé = l'ensemble du message de l'executor
    html = (
        f"<h2>Résultat : {state.objective}</h2>\n"
        f"<pre><code>{er.stdout.strip()}</code></pre>"
    )
    # Utiliser l'ensemble du message au lieu de seulement la dernière ligne
    summary = er.stdout.strip() if er.stdout.strip() else "Aucun résultat"

    render = {"html": html, "summary": summary, "artifacts": []}
    state.mem_obj.add("agent-writer", summary)
    state.mem_obj.add("assistant", summary)
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
    state = LoopState(objective=objective, mem_obj=mem, memory=mem.fetch())
    result = graph.invoke(state)
    print("✅ Résultat complet :\n", result["render"]["html"])

if __name__ == "__main__":
    import typer
    typer.run(run)
