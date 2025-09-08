# orchestrator/core_loop.py
from __future__ import annotations
import json
import os
import logging
import asyncio
from typing import Any, Dict, List, Tuple
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from orchestrator.llm.safe_invoke import safe_invoke_with_fallback
from orchestrator.llm.errors import ProviderExhaustedError
from orchestrator.llm.factory import build_llm
from orchestrator.llm.provider import OpenAIProvider, BoundLLMProvider
from orchestrator.settings import LLM_PROVIDER_ORDER
from agents.tools import TOOLS as LC_TOOLS  # StructuredTool list (async funcs)
from agents.tools_context import set_current_run_id
from orchestrator import crud, stream
from orchestrator.crud import init_db as init_crud_db
from orchestrator.run_registry import mark_run_done
from orchestrator.prompt_loader import load_prompt
from orchestrator import events
from orchestrator.storage.services import (
    start_span,
    end_span,
    save_blob,
    save_message,
    save_tool_call,
    save_tool_result,
)
from orchestrator.storage.db import get_session, init_db as init_sqlmodel_db
from orchestrator.storage.models import Run

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

AGENT_NAME = "chat_tools"

# Re-entrancy guard: per-run locks
RUN_LOCKS: dict[str, asyncio.Lock] = {}

# Simple intent keywords for tool exposure
CREATE_VERBS = {"create", "add", "génère", "crée", "ajoute"}
DELETE_VERBS = {"delete", "remove", "supprime", "nettoie", "archive"}


def _filter_tools_by_objective(objective: str, tools: list[Any]) -> list[Any]:
    """Filter available tools based on the user's objective.

    - For create-like intents, restrict to a safe subset.
    - Expose ``delete_item`` only when a delete-like verb is detected.
    - Otherwise, all tools except ``delete_item`` are allowed.
    """

    text = (objective or "").lower()

    if any(verb in text for verb in CREATE_VERBS):
        allowed = {"get_item", "list_items", "create_item", "update_item"}
        logger.info("Create intent detected; restricting tools to %s", allowed)
    else:
        allowed = {getattr(t, "name", None) for t in tools if getattr(t, "name", None) != "delete_item"}
        if any(verb in text for verb in DELETE_VERBS):
            allowed.add("delete_item")
            logger.info("Delete intent detected; including delete_item")

    return [t for t in tools if getattr(t, "name", None) in allowed]


def _tool_sig(tc: Dict[str, Any]) -> str:
    """Return a stable signature for a tool call used for deduplication."""
    return f"{tc.get('name')}|{json.dumps(tc.get('args') or {}, sort_keys=True, ensure_ascii=False)}"


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


def _verify_and_snapshot_created_item(item_id: int) -> dict:
    """Fetch a freshly created item and return a sanitized snapshot.

    Retries once if the item is not yet visible. Raises ``ValueError`` with
    ``"consistency_error"`` if the item still cannot be fetched.
    """

    for _ in range(2):
        item = crud.get_item(item_id)
        if item:
            return _sanitize(item.dict())
    raise ValueError("consistency_error")


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


def _extract_token_usage(msg: AIMessage) -> dict | None:
    """Best-effort extraction of token usage from a LangChain message."""
    meta = getattr(msg, "usage_metadata", None)
    if not meta:
        meta = getattr(msg, "response_metadata", {}).get("token_usage")
    if isinstance(meta, dict):
        return {
            "prompt": meta.get("prompt_tokens"),
            "completion": meta.get("completion_tokens"),
            "total": meta.get("total_tokens"),
        }
    return None


def _extract_model_name(msg: AIMessage) -> str | None:
    meta = getattr(msg, "response_metadata", {})
    return meta.get("model_name") or getattr(msg, "model", None)


async def _build_provider_chain(valid_tools: list[Any]) -> list[Any]:
    providers: list[Any] = []
    for name in LLM_PROVIDER_ORDER:
        if name == "openai" and os.getenv("OPENAI_API_KEY"):
            providers.append(
                OpenAIProvider(
                    base_model=os.getenv("OPENAI_MODEL", "gpt-5.1-mini"),
                    tool_model=os.getenv("OPENAI_TOOL_MODEL", "gpt-4o-mini"),
                    temperature=0,
                )
            )
            continue
        llm = build_llm(name, temperature=0)
        if llm:
            providers.append(BoundLLMProvider(llm, name=name))
    return providers


async def _run_chat_tools_impl(
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
    set_current_run_id(run_id)
    
    # Mark run as started
    crud.update_run_tool_phase(run_id, False)
    events.emit_status_update(run_id, "started", "Initializing agent")

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

    # Restrict tools based on the user's objective
    valid_tools = _filter_tools_by_objective(objective, valid_tools)
    if not valid_tools:
        logger.error("No tools available after intent filtering for objective '%s'", objective)
        return {"html": "<p>Error: No valid tools available for this objective</p>"}

    artifacts: dict[str, list[int]] = {
        "created_item_ids": [],
        "updated_item_ids": [],
        "deleted_item_ids": [],
    }
    created_ids: set[int] = set()

    providers = await _build_provider_chain(valid_tools)
    if not providers:
        logger.error("No LLM providers configured.")
        summary = "Error: No LLM providers configured"
        stream.publish(run_id, {"node": "plan"})
        stream.publish(run_id, {"node": "execute"})
        html = _build_html(summary, artifacts)
        clean_summary = _build_clean_summary(summary, artifacts)
        crud.finish_run(run_id, html, clean_summary, artifacts)
        stream.publish(run_id, {"node": "write", "summary": clean_summary})
        stream.close(run_id)
        stream.discard(run_id)
        return {"html": html}

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

Current project_id: {project_id if project_id else "Not specified"}
"""
    )

    user_message = (
        objective if project_id is None else f"{objective}\n\nproject_id={project_id}"
    )

    messages: list = [
        SystemMessage(content=enhanced_prompt),
        HumanMessage(content=user_message),
    ]

    save_message(
        run_id,
        role="user",
        content_ref=save_blob("text", user_message),
        agent_name=AGENT_NAME,
    )

    logger.info("System prompt length: %d characters", len(enhanced_prompt))
    logger.info("User message: %s", user_message)

    seen_tool_sigs: set[tuple[str, ...]] = set()

    for iteration in range(1, max_tool_calls + 1):
        logger.info("Starting iteration %d/%d", iteration, max_tool_calls)

        # Preflight validation: ensure no pending tool calls without responses
        _preflight_validate_messages(messages)

        try:
            rsp: AIMessage = await safe_invoke_with_fallback(
                providers, messages, tools=valid_tools
            )
            logger.info("AIMessage content: %r", getattr(rsp, "content", None))
            logger.info("AIMessage tool_calls: %s", getattr(rsp, "tool_calls", None))

            # Extract token usage and model for events
            tokens = _extract_token_usage(rsp)
            model = _extract_model_name(rsp)

            save_message(
                run_id,
                role="assistant",
                content_ref=save_blob("text", getattr(rsp, "content", "")),
                agent_name=AGENT_NAME,
                model=model,
                tokens=tokens,
            )

            # Always append the assistant message before any decisions
            messages.append(rsp)

            tcs = getattr(rsp, "tool_calls", None) or []
            content = (getattr(rsp, "content", "") or "").strip()
            if not tcs and content:
                events.emit_assistant_answer(run_id, content, model, tokens)
                # No tool calls and we have content - this is a final answer, finalize and exit
                summary = content
                html = _build_html(summary, artifacts)
                clean_summary = _build_clean_summary(summary, artifacts)
                events.emit_status_update(run_id, "completed", clean_summary)
                crud.finish_run(run_id, html, clean_summary, artifacts)
                stream.publish(run_id, {"node": "write", "summary": clean_summary})
                stream.close(run_id)
                stream.discard(run_id)
                events.cleanup_run(run_id)
                return {"html": html}
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

        if tcs:
            assistant_tool_call_ids = [
                getattr(tc, "id", None) or tc.get("id", f"tool_call_{i}")
                for i, tc in enumerate(tcs)
            ]
            logger.info(
                "iteration=%d, assistant_tool_call_ids=%s",
                iteration,
                assistant_tool_call_ids,
            )
            sig_tuple = tuple(
                _tool_sig(
                    {
                        "name": getattr(tc, "name", None)
                        if hasattr(tc, "name")
                        else tc.get("name"),
                        "args": getattr(tc, "args", None)
                        if hasattr(tc, "args")
                        else tc.get("args"),
                    }
                )
                for tc in tcs
            )
            if sig_tuple in seen_tool_sigs:
                logger.warning(
                    "Repeating identical tool_calls; stopping to avoid loop: %s",
                    sig_tuple,
                )
                summary = "Tool loop detected"
                html = _build_html(summary, artifacts)
                clean_summary = _build_clean_summary(summary, artifacts)
                events.emit_status_update(run_id, "completed", clean_summary)
                crud.finish_run(run_id, html, clean_summary, artifacts)
                stream.publish(run_id, {"node": "write", "summary": clean_summary})
                stream.close(run_id)
                stream.discard(run_id)
                events.cleanup_run(run_id)
                return {"html": html}
            seen_tool_sigs.add(sig_tuple)

            # Mark run as in tool phase
            crud.update_run_tool_phase(run_id, True)

            responded_tool_call_ids = []

            # Execute each tool call synchronously and append ToolMessage immediately
            for i, tc in enumerate(tcs):
                # Handle different tool call formats
                if hasattr(tc, "name"):
                    name = tc.name
                    args = getattr(tc, "args", {}) or {}
                    tool_call_id = getattr(tc, "id", f"tool_call_{i}")
                elif isinstance(tc, dict):
                    name = tc.get("name")
                    args = tc.get("args", {}) or {}
                    tool_call_id = tc.get("id", f"tool_call_{i}")
                else:
                    logger.error("Unknown tool call format: %s", tc)
                    continue

                logger.info(
                    "Processing tool call %d: %s with args %s (tool_call_id: %s)",
                    i + 1,
                    name,
                    args,
                    tool_call_id,
                )

                # Emit tool call event
                try:
                    event_args = json.loads(json.dumps(args))
                    events.emit_tool_call(run_id, name, event_args, tool_call_id, model, tokens)
                    logger.info(f"Emitted tool_call event for {name} with tool_call_id {tool_call_id}")
                except Exception as e:
                    logger.error(f"Failed to emit tool_call event: {e}")

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

                # Start span for tool execution
                tool_span_id = start_span(
                    run_id, f"tool_{name}", input_ref=save_blob("json", args)
                )

                call_ref = save_blob("json", args)
                call_id = save_tool_call(
                    run_id, AGENT_NAME, name, input_ref=call_ref, span_id=tool_span_id
                )

                blocked = False
                status = "ok"
                result: dict
                if name == "delete_item":
                    explicit = bool(args.get("explicit_confirm", False))
                    item_id = args.get("id")
                    if item_id in created_ids and not explicit:
                        logger.warning(
                            "blocked_by_write_barrier: attempt to delete id=%s", item_id
                        )
                        result = {
                            "ok": False,
                            "error": "blocked_by_write_barrier",
                            "status": 400,
                        }
                        status = "error"
                        blocked = True

                if not blocked:
                    try:
                        logger.info("Invoking tool '%s' with args: %s", name, args)
                        raw = await tool.ainvoke(args)
                    except Exception as e:
                        logger.error(
                            "Tool '%s' execution failed: %s", name, str(e), exc_info=True
                        )
                        result = {"ok": False, "error": str(e)}
                        status = "error"
                    else:
                        try:
                            result = json.loads(raw)
                        except Exception:
                            result = {"ok": True, "raw": raw}
                        if name == "create_item" and result.get("item_id"):
                            try:
                                result["snapshot"] = _verify_and_snapshot_created_item(
                                    result["item_id"]
                                )
                            except Exception as e:
                                logger.error("Post-create verification failed: %s", e)
                                result = {"ok": False, "error": str(e)}
                                status = "error"
                result_str = json.dumps(result)

                # End tool span
                end_span(
                    tool_span_id,
                    status=status,
                    output_ref=save_blob("text", result_str),
                )

                save_tool_result(
                    call_id, status, output_ref=save_blob("text", result_str)
                )

                # Emit tool result event
                try:
                    events.emit_tool_result(run_id, name, result, tool_call_id, status)
                    logger.info(f"Emitted tool_result event for {name} with status {status}")
                except Exception as e:
                    logger.error(f"Failed to emit tool_result event: {e}")

                ok = bool(result.get("ok", True))
                if ok:
                    # MAJ artifacts si handler a renvoyé un item_id
                    if name == "create_item" and "item_id" in result:
                        artifacts["created_item_ids"].append(result["item_id"])
                        created_ids.add(result["item_id"])
                    elif name == "update_item" and "item_id" in result:
                        artifacts["updated_item_ids"].append(result["item_id"])
                    elif name == "delete_item" and "item_id" in result:
                        artifacts["deleted_item_ids"].append(result["item_id"])
                else:
                    summary = result.get("error") or "Tool execution failed"
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

                # Append ToolMessage with exact tool_call_id from the assistant
                messages.append(
                    ToolMessage(
                        tool_call_id=tool_call_id, content=result_str, name=name
                    )
                )
                responded_tool_call_ids.append(tool_call_id)

            logger.info(
                "Tool execution completed. responded_tool_call_ids=%s",
                responded_tool_call_ids,
            )
            
            # Mark run as out of tool phase
            crud.update_run_tool_phase(run_id, False)

            # Continue la boucle pour un prochain appel tool / ou un résumé final
            continue

        # --- STOP CASE: no tool calls -> finalize and return
        response_content = content or "No response"

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

        events.emit_status_update(run_id, "completed", clean_summary)
        crud.finish_run(run_id, html, clean_summary, artifacts)

        stream.publish(run_id, {"node": "write", "summary": clean_summary})
        stream.close(run_id)
        stream.discard(run_id)
        events.cleanup_run(run_id)
        return {"html": html}

    # Si on sort par dépassement
    summary = "Max tool calls exceeded"
    html = _build_html(summary, artifacts)
    clean_summary = _build_clean_summary(summary, artifacts)
    events.emit_error(run_id, "Max tool calls exceeded", "Too many tool invocations")
    crud.record_run_step(run_id, "error", summary)
    crud.finish_run(run_id, html, clean_summary, artifacts)
    stream.publish(run_id, {"node": "write", "summary": clean_summary})
    stream.close(run_id)
    stream.discard(run_id)
    events.cleanup_run(run_id)
    return {"html": html}


async def run_chat_tools(
    objective: str, project_id: int | None, run_id: str, max_tool_calls: int = 10
) -> dict:
    # Re-entrancy guard: prevent multiple concurrent runs for the same run_id
    if run_id not in RUN_LOCKS:
        RUN_LOCKS[run_id] = asyncio.Lock()

    if RUN_LOCKS[run_id].locked():
        logger.warning(
            "run_chat_tools already in progress for run_id=%s, ignoring duplicate call",
            run_id,
        )
        return {"html": "<p>Run already in progress</p>"}

    async with RUN_LOCKS[run_id]:
        return await _run_chat_tools_locked(
            objective, project_id, run_id, max_tool_calls
        )


async def _run_chat_tools_locked(
    objective: str, project_id: int | None, run_id: str, max_tool_calls: int = 10
) -> dict:
    inputs = {
        "objective": objective,
        "project_id": project_id,
        "max_tool_calls": max_tool_calls,
    }
    init_crud_db()  # Initialize CRUD SQLite tables
    init_sqlmodel_db()  # Initialize SQLModel tables
    with get_session() as s:
        if s.get(Run, run_id) is None:
            s.add(Run(id=run_id, project_id=project_id))
            s.commit()
    span_id = start_span(run_id, AGENT_NAME, input_ref=save_blob("json", inputs))
    result: dict | None = None
    err: Exception | None = None
    try:
        result = await _run_chat_tools_impl(
            objective, project_id, run_id, max_tool_calls
        )
    except Exception as e:  # pragma: no cover - propagate unexpected failures
        err = e
        raise
    finally:
        output = result if err is None else {"error": str(err)}
        out_ref = save_blob("json", output)
        end_span(span_id, status="error" if err else "ok", output_ref=out_ref)
        mark_run_done(run_id)
    return result


def _preflight_validate_messages(messages: list) -> None:
    """Validate that there are no pending assistant tool_calls without corresponding tool responses."""
    if not messages:
        return

    # Check if the last message is an assistant with tool_calls but no following tool messages
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if isinstance(msg, AIMessage):
            tool_calls = getattr(msg, "tool_calls", None) or []
            if tool_calls:
                # Find tool_call_ids that need responses
                expected_ids = {
                    getattr(tc, "id", None) or tc.get("id") for tc in tool_calls
                }
                expected_ids = {tcid for tcid in expected_ids if tcid}

                # Check if subsequent messages contain all required tool responses
                found_ids = set()
                for j in range(i + 1, len(messages)):
                    next_msg = messages[j]
                    if isinstance(next_msg, ToolMessage):
                        tcid = getattr(next_msg, "tool_call_id", None)
                        if tcid:
                            found_ids.add(tcid)
                    elif isinstance(next_msg, AIMessage):
                        # Found another AI message, stop looking
                        break

                missing_ids = expected_ids - found_ids
                if missing_ids:
                    error_msg = f"Preflight validation failed: Assistant message has tool_calls with ids {list(expected_ids)} but missing tool responses for ids {list(missing_ids)}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            break  # Only check the most recent assistant message
