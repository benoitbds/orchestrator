# orchestrator/core_loop.py
from __future__ import annotations
import json
import os
import logging
from typing import Any
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from orchestrator.llm.safe_invoke import safe_invoke_with_fallback
from orchestrator.llm.errors import ProviderExhaustedError
from orchestrator.llm.factory import build_llm
from orchestrator.settings import LLM_PROVIDER_ORDER
from agents.tools import (
    TOOLS as LC_TOOLS,
    set_current_run,
)  # StructuredTool list (async funcs)
from orchestrator import crud, stream
from orchestrator.prompt_loader import load_prompt

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _sanitize(v)
            for k, v in obj.items()
            if "key" not in k.lower() and "secret" not in k.lower()
        }
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


def _build_clean_summary(summary: str, artifacts: dict[str, list[int]]) -> str:
    """Build a clean summary without HTML formatting for better display."""

    def fmt(ids: list[int]) -> str:
        return ", ".join(map(str, ids)) if ids else "none"

    parts = []
    if artifacts["created_item_ids"]:
        parts.append(f"Created items: {fmt(artifacts['created_item_ids'])}")
    if artifacts["updated_item_ids"]:
        parts.append(f"Updated items: {fmt(artifacts['updated_item_ids'])}")
    if artifacts["deleted_item_ids"]:
        parts.append(f"Deleted items: {fmt(artifacts['deleted_item_ids'])}")

    if parts:
        artifacts_summary = ". ".join(parts) + "."
        return f"{artifacts_summary} {summary}".strip()

    return summary


async def _build_provider_chain(valid_tools: list[Any]) -> list[Any]:
    providers: list[Any] = []
    for name in LLM_PROVIDER_ORDER:
        llm = build_llm(name, temperature=0)
        if llm:
            try:
                providers.append(llm.bind_tools(valid_tools))
            except Exception:
                providers.append(llm)
    return providers


async def run_chat_tools(
    objective: str, project_id: int | None, run_id: str, max_tool_calls: int = 10
) -> dict:
    logger.info(
        "FULL-AGENT MODE: starting run_chat_tools(project_id=%s, run_id=%s)",
        project_id,
        run_id,
    )
    logger.info("OPENAI_API_KEY set: %s", bool(os.getenv("OPENAI_API_KEY")))
    logger.info("TOOLS names: %s", [getattr(t, "name", None) for t in LC_TOOLS])
    logger.info("TOOLS count: %d", len(LC_TOOLS))

    # Set the current run context for tools
    set_current_run(run_id)

    # 1) Prépare le modèle + binding outils (LangChain)
    # Verify tools are valid before binding
    valid_tools = []
    for tool in LC_TOOLS:
        if (
            hasattr(tool, "name")
            and hasattr(tool, "description")
            and hasattr(tool, "args_schema")
        ):
            valid_tools.append(tool)
            logger.info(
                "Valid tool: %s - %s (schema: %s)",
                tool.name,
                tool.description,
                tool.args_schema.__name__,
            )
        else:
            logger.warning("Invalid tool found: %s", tool)

    if not valid_tools:
        logger.error("No valid tools found for binding!")
        return {"html": "<p>Error: No valid tools available</p>"}

    providers = await _build_provider_chain(valid_tools)
    if not providers:
        logger.error("No LLM providers configured.")
        return {"html": "<p>Error: No LLM providers configured</p>"}

    logger.info("Configured %d LLM provider(s)", len(providers))

    # 2) Historique messages
    tool_system_prompt = load_prompt("tool_system_prompt")
    enhanced_prompt = (
        tool_system_prompt
        + f"""

IMPORTANT: You have access to {len(valid_tools)} tools: {[t.name for t in valid_tools]}

For ANY request involving backlog management, you MUST use the appropriate tool. 
DO NOT provide text-only responses like "placeholder" or "I'll help you with that".
ALWAYS call a tool to perform the actual action.

Current project_id: {project_id if project_id else 'Not specified'}
"""
    )

    user_message = (
        objective if project_id is None else f"{objective}\n\nproject_id={project_id}"
    )

    messages: list = [
        SystemMessage(content=enhanced_prompt),
        HumanMessage(content=user_message),
    ]

    logger.info("System prompt length: %d characters", len(enhanced_prompt))
    logger.info("User message: %s", user_message)

    artifacts: dict[str, list[int]] = {
        "created_item_ids": [],
        "updated_item_ids": [],
        "deleted_item_ids": [],
    }
    consecutive_errors = 0

    for iteration in range(max_tool_calls):
        logger.info("Starting iteration %d/%d", iteration + 1, max_tool_calls)

        try:
            rsp: AIMessage = await safe_invoke_with_fallback(providers, messages)
            logger.info("AIMessage content: %r", getattr(rsp, "content", None))
            logger.info("AIMessage tool_calls: %s", getattr(rsp, "tool_calls", None))
        except ProviderExhaustedError:
            logger.exception("All LLM providers exhausted for run %s", run_id)
            summary = "LLM providers exhausted"
            html = _build_html(summary, artifacts)
            clean_summary = _build_clean_summary(summary, artifacts)
            crud.finish_run(run_id, html, clean_summary, artifacts)
            stream.publish(run_id, {"node": "write", "summary": clean_summary})
            stream.close(run_id)
            stream.discard(run_id)
            return {"html": html}
        except Exception as e:
            logger.error("LLM invoke failed: %s", str(e), exc_info=True)
            summary = f"LLM invoke failed: {str(e)}"
            html = _build_html(summary, artifacts)
            clean_summary = _build_clean_summary(summary, artifacts)
            crud.finish_run(run_id, html, clean_summary, artifacts)
            stream.publish(run_id, {"node": "write", "summary": clean_summary})
            stream.close(run_id)
            stream.discard(run_id)
            return {"html": html}

        tcs = getattr(rsp, "tool_calls", None) or []
        logger.info("Found %d tool calls", len(tcs))
        if tcs:
            # Add the AI message with tool calls to the conversation first
            messages.append(rsp)

            # On gère les tool calls (souvent 1 par tour)
            for i, tc in enumerate(tcs):
                # Handle different tool call formats
                if hasattr(tc, "name"):
                    name = tc.name
                    args = getattr(tc, "args", {}) or {}
                    call_id = getattr(tc, "id", f"tool_call_{i}")
                elif isinstance(tc, dict):
                    name = tc.get("name")
                    args = tc.get("args", {}) or {}
                    call_id = tc.get("id", f"tool_call_{i}")
                else:
                    logger.error("Unknown tool call format: %s", tc)
                    continue

                logger.info(
                    "Processing tool call %d: %s with args %s (id: %s)",
                    i + 1,
                    name,
                    args,
                    call_id,
                )

                # inject run_id & (si absent) project_id pour nos wrappers asynchrones
                if "run_id" not in args:
                    args["run_id"] = run_id
                if project_id is not None and "project_id" not in args:
                    args["project_id"] = project_id

                # Trouver le StructuredTool demandé
                tool = next(
                    (t for t in valid_tools if getattr(t, "name", None) == name), None
                )
                if tool is None:
                    # Sécurité : on finalise avec message d’erreur
                    err = f"Unknown tool requested: {name}. Available tools: {[getattr(t, 'name', None) for t in valid_tools]}"
                    logger.error(err)
                    crud.record_run_step(run_id, "error", err)
                    summary = err
                    html = _build_html(summary, artifacts)
                    clean_summary = _build_clean_summary(summary, artifacts)
                    crud.finish_run(run_id, html, clean_summary, artifacts)
                    stream.publish(run_id, {"node": "write", "summary": clean_summary})
                    stream.close(run_id)
                    stream.discard(run_id)
                    return {"html": html}

                # Exécuter le StructuredTool (il appelle le handler, loggue et stream)
                try:
                    logger.info("Invoking tool '%s' with args: %s", name, args)
                    result_str = await tool.ainvoke(
                        args
                    )  # notre func async renvoie une string JSON
                    logger.info("Tool '%s' completed successfully", name)
                except Exception as e:
                    logger.error(
                        "Tool '%s' execution failed: %s", name, str(e), exc_info=True
                    )
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
                        clean_summary = _build_clean_summary(summary, artifacts)
                        crud.finish_run(run_id, html, clean_summary, artifacts)
                        stream.publish(
                            run_id, {"node": "write", "summary": clean_summary}
                        )
                        stream.close(run_id)
                        stream.discard(run_id)
                        return {"html": html}

                # Feedback au modèle pour enchaîner
                messages.append(
                    ToolMessage(tool_call_id=call_id, content=result_str, name=name)
                )

            # Continue la boucle pour un prochain appel tool / ou un résumé final
            continue

        # Pas de tool call → vérifier si c'est une réponse placeholder
        response_content = rsp.content or "No response"

        # Detect placeholder responses and provide guidance
        if response_content.lower() in ["placeholder", "i'll help you", "i can help"]:
            logger.warning(
                "LLM returned placeholder response instead of using tools: %s",
                response_content,
            )
            summary = f"Error: Agent provided placeholder response '{response_content}' instead of using available tools. This suggests the request requires tool usage but the agent didn't recognize this."
        else:
            summary = response_content

        html = _build_html(summary, artifacts)
        clean_summary = _build_clean_summary(summary, artifacts)
        crud.finish_run(run_id, html, clean_summary, artifacts)
        stream.publish(run_id, {"node": "write", "summary": clean_summary})
        stream.close(run_id)
        stream.discard(run_id)
        return {"html": html}

    # Si on sort par dépassement
    summary = "Max tool calls exceeded"
    html = _build_html(summary, artifacts)
    clean_summary = _build_clean_summary(summary, artifacts)
    crud.record_run_step(run_id, "error", summary)
    crud.finish_run(run_id, html, clean_summary, artifacts)
    stream.publish(run_id, {"node": "write", "summary": clean_summary})
    stream.close(run_id)
    stream.discard(run_id)
    return {"html": html}
