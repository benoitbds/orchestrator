# orchestrator/core_loop.py
from __future__ import annotations
import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import List, Optional, Any
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ConfigDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage

from agents.planner import make_plan, TOOL_SYSTEM_PROMPT
from agents.schemas import ExecResult, Plan
from agents.tools import TOOLS as LC_TOOLS  # StructuredTool list (async funcs)
import threading
from orchestrator import crud, stream

import logging

logger = logging.getLogger(__name__)

load_dotenv()


def _sanitize(obj: Any) -> Any:
    """Recursively remove keys that might contain secrets."""
    if isinstance(obj, dict):
        return {
            k: _sanitize(v)
            for k, v in obj.items()
            if "key" not in k.lower() and "secret" not in k.lower()
        }
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


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

# ---------- Tool loop executor ----------
def _build_html(summary: str, artifacts: dict[str, list[int]]) -> str:
    def fmt(ids: list[int]) -> str:
        return ", ".join(map(str, ids)) if ids else "none"

    return (
        "<ul>"
        f"<li>Created items: {fmt(artifacts['created_item_ids'])}</li>"
        f"<li>Updated items: {fmt(artifacts['updated_item_ids'])}</li>"
        f"<li>Deleted items: {fmt(artifacts['deleted_item_ids'])}</li>"
        "</ul>"
        f"<p>{summary}</p>"
    )


async def run_chat_tools(
    objective: str,
    project_id: int | None,
    run_id: str,
    max_tool_calls: int = 10,
) -> dict:
    logger.info("FULL-AGENT MODE: starting run_chat_tools(project_id=%s)", project_id)
    logger.info("OPENAI_API_KEY set: %s", bool(os.getenv("OPENAI_API_KEY")))
    logger.info("TOOLS names: %s", [getattr(t, "name", None) for t in LC_TOOLS])

    # 1) Prepare model and bind tools
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    llm = llm.bind_tools(LC_TOOLS)

    # 2) Message history
    messages: list = [
        SystemMessage(content=TOOL_SYSTEM_PROMPT + "\nIf the user asks to create/update/delete/move/list/get/summarize, you MUST call a tool."),
        HumanMessage(content=objective if project_id is None else f"{objective}\n\nproject_id={project_id}"),
    ]

    artifacts: dict[str, list[int]] = {"created_item_ids": [], "updated_item_ids": [], "deleted_item_ids": []}
    consecutive_errors = 0

    for _ in range(max_tool_calls):
        rsp: AIMessage = await llm.ainvoke(messages)
        logger.info("AIMessage content: %r", getattr(rsp, "content", None))
        logger.info("AIMessage tool_calls: %s", getattr(rsp, "tool_calls", None))

        tcs = getattr(rsp, "tool_calls", None) or []
        if tcs:
            for tc in tcs:
                name = getattr(tc, "name", None)
                args = getattr(tc, "args", {}) or {}
                call_id = getattr(tc, "id", "tool_call_0")

                if "run_id" not in args:
                    args["run_id"] = run_id
                if project_id is not None and "project_id" not in args:
                    args["project_id"] = project_id

                tool = next((t for t in LC_TOOLS if getattr(t, "name", None) == name), None)
                if tool is None:
                    err = f"Unknown tool requested: {name}"
                    crud.record_run_step(run_id, "error", err)
                    summary = err
                    html = _build_html(summary, artifacts)
                    crud.finish_run(run_id, html, summary, artifacts)
                    stream.publish(run_id, {"node": "write", "summary": summary})
                    stream.close(run_id); stream.discard(run_id)
                    return {"html": html}

                try:
                    result_str = await tool.ainvoke(args)
                except Exception as e:
                    result_str = json.dumps({"ok": False, "error": str(e)})

                try:
                    result = json.loads(result_str)
                except Exception:
                    result = {"ok": True, "raw": result_str}

                ok = bool(result.get("ok", True))
                if ok:
                    consecutive_errors = 0
                    if name == "create_item" and "item_id" in result:
                        artifacts["created_item_ids"].append(result["item_id"])
                    elif name == "update_item" and "item_id" in result:
                        artifacts["updated_item_ids"].append(result["item_id"])
                    elif name == "delete_item" and "item_id" in result:
                        artifacts["deleted_item_ids"].append(result["item_id"])
                else:
                    consecutive_errors += 1
                    if consecutive_errors >= 3:
                        summary = "Too many consecutive tool errors"
                        crud.record_run_step(run_id, "error", summary)
                        html = _build_html(summary, artifacts)
                        crud.finish_run(run_id, html, summary, artifacts)
                        stream.publish(run_id, {"node": "write", "summary": summary})
                        stream.close(run_id); stream.discard(run_id)
                        return {"html": html}

                messages.append(ToolMessage(tool_call_id=call_id, content=result_str, name=name))
            continue

        summary = rsp.content or "No tool call."
        html = _build_html(summary, artifacts)
        crud.finish_run(run_id, html, summary, artifacts)
        stream.publish(run_id, {"node":"write","summary": summary})
        stream.close(run_id); stream.discard(run_id)
        return {"html": html}

    summary = "Max tool calls exceeded"
    html = _build_html(summary, artifacts)
    crud.record_run_step(run_id, "error", summary)
    crud.finish_run(run_id, html, summary, artifacts)
    stream.publish(run_id, {"node":"write","summary": summary})
    stream.close(run_id); stream.discard(run_id)
    return {"html": html}


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
