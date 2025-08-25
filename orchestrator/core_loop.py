# orchestrator/core_loop.py
from __future__ import annotations
import sqlite3
import json
import asyncio
from typing import List, Optional, Any
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ConfigDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from agents.planner import make_plan, TOOL_SYSTEM_PROMPT
from agents.schemas import ExecResult, Plan
from agents.tools import TOOLS, HANDLERS
import threading
from orchestrator import crud

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


async def _run_tool(name: str, args: dict) -> dict:
    handler = HANDLERS.get(name)
    if handler is None:
        return {"ok": False, "error": f"unknown tool {name}"}
    try:
        return await asyncio.wait_for(handler(args), timeout=8)
    except asyncio.TimeoutError:
        return {"ok": False, "error": "timeout"}
    except Exception as exc:  # pragma: no cover - defensive
        return {"ok": False, "error": str(exc)}


async def run_chat_tools(
    objective: str,
    project_id: int | None,
    run_id: str,
    max_tool_calls: int = 10,
) -> dict:
    """Run a function-calling loop with the LLM."""
    import os

    logger.info("FULL-AGENT MODE: starting run_chat_tools(project_id=%s)", project_id)
    logger.info("OPENAI_API_KEY set: %s", bool(os.getenv("OPENAI_API_KEY")))
    from agents.tools import TOOLS, HANDLERS  # noqa: F401
    # TOOLS is a list of tool schemas. Each must have a predictable name field:
    tool_names = []
    for t in TOOLS:
        name = None
        if isinstance(t, dict):
            name = t.get("name") or (t.get("function") or {}).get("name")
        tool_names.append(name)
    logger.info("TOOLS loaded: %s", tool_names)

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    model = model.bind_tools(TOOLS)
    logger.info("Model bound to %d tools.", len(TOOLS))
    messages: list[dict[str, str]] = [
        {"role": "system", "content": TOOL_SYSTEM_PROMPT},
        {"role": "user", "content": objective},
    ]
    artifacts: dict[str, list[int]] = {
        "created_item_ids": [],
        "updated_item_ids": [],
        "deleted_item_ids": [],
    }
    consecutive_errors = 0
    for _ in range(max_tool_calls):
        rsp = model.invoke(messages)
        tc = rsp.additional_kwargs.get("tool_calls")
        logger.info("LLM raw content: %r", rsp.content)
        logger.info("LLM tool_calls: %s", tc)
        tool_calls = tc or []
        if tool_calls:
            tc = tool_calls[0]
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            safe_args = _sanitize(args)
            logger.info("DISPATCH tool=%s args=%s", name, safe_args)
            crud.record_run_step(
                run_id,
                f"tool:{name}:request",
                json.dumps({"name": name, "args": safe_args}),
            )
            result = await _run_tool(name, args)
            ok = result.get("ok")
            error = result.get("error")
            data = {k: v for k, v in result.items() if k not in {"ok", "error"}}
            safe_result = _sanitize(data)
            crud.record_run_step(
                run_id,
                f"tool:{name}:response",
                json.dumps({"ok": ok, "result": safe_result, "error": error}),
            )
            if ok:
                consecutive_errors = 0
                if name == "create_item":
                    artifacts["created_item_ids"].append(result["item_id"])
                elif name == "update_item":
                    artifacts["updated_item_ids"].append(result["item_id"])
                elif name == "delete_item":
                    artifacts["deleted_item_ids"].append(result["item_id"])
            else:
                consecutive_errors += 1
                crud.record_run_step(run_id, "error", result.get("error", "error"))
                if consecutive_errors >= 3:
                    summary = "Too many consecutive tool errors"
                    crud.record_run_step(run_id, "error", summary)
                    html = _build_html(summary, artifacts)
                    crud.finish_run(run_id, html, summary, artifacts)
                    return {"html": html}
            messages.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result)}
            )
            continue
        summary = rsp.content
        html = _build_html(summary, artifacts)
        crud.finish_run(run_id, html, summary, artifacts)
        return {"html": html}
    crud.record_run_step(run_id, "error", "max tool calls exceeded")
    summary = "Max tool calls exceeded"
    html = _build_html(summary, artifacts)
    crud.finish_run(run_id, html, summary, artifacts)
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
