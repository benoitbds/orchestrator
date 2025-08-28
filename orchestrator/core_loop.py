# orchestrator/core_loop.py
from __future__ import annotations
import json, asyncio, os, logging
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from agents.planner import TOOL_SYSTEM_PROMPT
from agents.tools import TOOLS as LC_TOOLS  # StructuredTool list (async funcs)
from orchestrator import crud, stream

logger = logging.getLogger(__name__)

def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items() if "key" not in k.lower() and "secret" not in k.lower()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj

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

async def run_chat_tools(objective: str, project_id: int | None, run_id: str, max_tool_calls: int = 10) -> dict:
    logger.info("FULL-AGENT MODE: starting run_chat_tools(project_id=%s)", project_id)
    logger.info("OPENAI_API_KEY set: %s", bool(os.getenv("OPENAI_API_KEY")))
    logger.info("TOOLS names: %s", [getattr(t, "name", None) for t in LC_TOOLS])

    # 1) Prépare le modèle + binding outils (LangChain)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    llm = llm.bind_tools(LC_TOOLS)

    # 2) Historique messages
    messages: list = [
        SystemMessage(content=TOOL_SYSTEM_PROMPT + "\nIf the user asks to create/update/delete/move/list/get/summarize, you MUST call a tool."),
        HumanMessage(content=objective if project_id is None else f"{objective}\n\nproject_id={project_id}"),
    ]

    artifacts: dict[str, list[int]] = {"created_item_ids": [], "updated_item_ids": [], "deleted_item_ids": []}
    consecutive_errors = 0

    for _ in range(max_tool_calls):
        # ChatOpenAI fournit uniquement une API synchrone. Exécuter l'appel dans un
        # thread permet de ne pas bloquer la boucle d'événements.
        rsp: AIMessage = await asyncio.to_thread(llm.invoke, messages)
        logger.info("AIMessage content: %r", getattr(rsp, "content", None))
        logger.info("AIMessage tool_calls: %s", getattr(rsp, "tool_calls", None))

        tcs = getattr(rsp, "tool_calls", None) or []
        if tcs:
            # On gère les tool calls (souvent 1 par tour)
            for tc in tcs:
                name = getattr(tc, "name", None)
                args = getattr(tc, "args", {}) or {}
                call_id = getattr(tc, "id", "tool_call_0")

                # inject run_id & (si absent) project_id pour nos wrappers asynchrones
                if "run_id" not in args:
                    args["run_id"] = run_id
                if project_id is not None and "project_id" not in args:
                    args["project_id"] = project_id

                # Trouver le StructuredTool demandé
                tool = next((t for t in LC_TOOLS if getattr(t, "name", None) == name), None)
                if tool is None:
                    # Sécurité : on finalise avec message d’erreur
                    err = f"Unknown tool requested: {name}"
                    crud.record_run_step(run_id, "error", err)
                    summary = err
                    html = _build_html(summary, artifacts)
                    crud.finish_run(run_id, html, summary, artifacts)
                    stream.publish(run_id, {"node": "write", "summary": summary})
                    stream.close(run_id); stream.discard(run_id)
                    return {"html": html}

                # Exécuter le StructuredTool (il appelle le handler, loggue et stream)
                try:
                    result_str = await tool.ainvoke(args)  # notre func async renvoie une string JSON
                except Exception as e:
                    result_str = json.dumps({"ok": False, "error": str(e)})

                # Parse résultat & maj artifacts
                try:
                    result = json.loads(result_str)
                except Exception:
                    result = {"ok": True, "raw": result_str}

                ok = bool(result.get("ok", True))
                if ok:
                    consecutive_errors = 0
                    # MAJ artifacts si handler a renvoyé un item_id
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

                # Feedback au modèle pour enchaîner
                messages.append(ToolMessage(tool_call_id=call_id, content=result_str, name=name))

            # Continue la boucle pour un prochain appel tool / ou un résumé final
            continue

        # Pas de tool call → on termine par un résumé textuel (ou question)
        summary = rsp.content or "No tool call."
        html = _build_html(summary, artifacts)
        crud.finish_run(run_id, html, summary, artifacts)
        stream.publish(run_id, {"node":"write","summary": summary})
        stream.close(run_id); stream.discard(run_id)
        return {"html": html}

    # Si on sort par dépassement
    summary = "Max tool calls exceeded"
    html = _build_html(summary, artifacts)
    crud.record_run_step(run_id, "error", summary)
    crud.finish_run(run_id, html, summary, artifacts)
    stream.publish(run_id, {"node":"write","summary": summary})
    stream.close(run_id); stream.discard(run_id)
    return {"html": html}
