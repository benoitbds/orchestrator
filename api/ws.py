from __future__ import annotations

import asyncio
import hashlib
from uuid import uuid4
from typing import Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

import logging
from orchestrator.core_loop import run_chat_tools
from orchestrator import crud, stream
from orchestrator.run_registry import get_or_create_run
from orchestrator.events import start_run
import types

try:  # pragma: no cover - exercised via integration paths
    from firebase_admin import auth as fb_auth
except (ImportError, AttributeError):  # pragma: no cover - test environments without Firebase
    fb_auth = types.SimpleNamespace(verify_id_token=lambda token: {"uid": "test"})


router = APIRouter()
logger = logging.getLogger(__name__)

# Track running tasks to cancel them when needed (keyed by client_id)
RUNNING_TASKS: Dict[str, asyncio.Task] = {}


async def close_ws(ws: WebSocket, code: int, reason: str | None = None) -> None:
    """Close websocket if still connected."""
    if ws.client_state == WebSocketState.CONNECTED:
        await ws.close(code=code, reason=reason)


def stable_client_id(ws: WebSocket, payload: dict) -> str:
    """
    Build a stable client id if the frontend doesn't provide one.
    We prefer (header/client/payload) if present, otherwise fallback to a hash of UA+IP.
    """
    provided = (
        ws.headers.get("x-client-session-id")
        or payload.get("client_session_id")
        or ws.cookies.get("client_session_id")
        or payload.get("temp_run_id")
    )
    if provided:
        return str(provided)

    ua = ws.headers.get("user-agent", "")
    xff = ws.headers.get("x-forwarded-for", "")
    # starlette exposes ws.client as (host, port) tuple via ws.client.host
    ip = getattr(ws.client, "host", "") or ""
    base = f"{ua}|{xff or ip}".encode("utf-8")
    digest = hashlib.sha256(base).hexdigest()[:32]
    return f"auto-{digest}"


@router.websocket("/stream")
async def stream_chat(ws: WebSocket):
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=4401, reason="unauthorized")
        return
    try:
        fb_auth.verify_id_token(token)
    except Exception:  # pragma: no cover - firebase-specific errors
        await ws.close(code=4401, reason="unauthorized")
        return

    # Accept exactly once per connection
    await ws.accept()
    logger.info("WebSocket connection accepted")

    run_id: Optional[str] = None
    queue: Optional[asyncio.Queue] = None

    try:
        logger.info("WebSocket waiting for JSON payload...")
        payload = await ws.receive_json()
        logger.info("WebSocket received payload: %s", payload)

        action = payload.get("action", "start")  # "start" or "subscribe"
        passed_run_id = payload.get("run_id")
        objective = payload.get("objective")
        project_id = payload.get("project_id")

        client_id = stable_client_id(ws, payload)
        logger.info("Resolved client_id=%s (action=%s)", client_id, action)

        # ============
        # SUBSCRIBE
        # ============
        if action == "subscribe":
            run_id = passed_run_id
            if not run_id:
                await close_ws(ws, code=1008, reason="run_id required for subscribe")
                return

            run = crud.get_run(run_id)
            if not run:
                await close_ws(ws, code=4404, reason="run not found")
                return

            queue = stream.get(run_id)
            if queue is None:
                queue = stream.register(run_id)

            await ws.send_json({"run_id": run_id, "status": "subscribed"})

        # ========
        # START
        # ========
        elif action == "start":
            # Important: with stable client_id, this will return created=False
            # if an unfinished run already exists for this client.
            entry, created = get_or_create_run(client_id, project_id, objective, passed_run_id)
            if not entry:
                await close_ws(ws, code=1008, reason="objective or run_id required")
                return

            run_id = entry["run_id"]

            # If the run is already done, short-circuit.
            if entry.get("status") == "done":
                await ws.send_json({"status": "done", "run_id": run_id})
                await close_ws(ws, code=1000)
                return

            # Attach to the stream queue (create if missing)
            queue = stream.get(run_id)
            if queue is None:
                queue = stream.register(run_id)

            if created:
                # Persist run and initialize event tracking
                crud.create_run(run_id, objective, project_id, None)
                start_run(run_id)

                # Fresh run for this client: cancel any previous task for the same client (defensive)
                if client_id in RUNNING_TASKS:
                    old_task = RUNNING_TASKS[client_id]
                    if not old_task.done():
                        logger.info("Cancelling existing task for client_id: %s", client_id)
                        old_task.cancel()
                        try:
                            await old_task
                        except asyncio.CancelledError:
                            pass

                await ws.send_json({"run_id": run_id, "status": "started"})

                async def runner() -> None:
                    try:
                        await run_chat_tools(objective, project_id, run_id)
                    except asyncio.CancelledError:
                        logger.info("Task cancelled for run_id: %s", run_id)
                        raise
                    except Exception as exc:
                        # Ensure run finishes with error state.
                        crud.finish_run(run_id, "", str(exc))
                    finally:
                        # Signal end of stream to all subscribers then close queue holder.
                        stream.close(run_id)
                        # Remove from running tasks when done
                        current = asyncio.current_task()
                        if current is not None and RUNNING_TASKS.get(client_id) is current:
                            del RUNNING_TASKS[client_id]

                task = asyncio.create_task(runner(), name=f"run-{run_id}")
                RUNNING_TASKS[client_id] = task
            else:
                # Existing unfinished run for this client_id → just attach/stream
                await ws.send_json({"run_id": run_id, "status": "existing"})

        else:
            await close_ws(ws, code=1008, reason="invalid action")
            return

        # ===========
        # STREAM LOOP
        # ===========
        logger.info("WebSocket starting to stream events for run_id: %s", run_id)
        assert queue is not None, "Queue must be set before streaming"

        while True:
            chunk = await queue.get()
            if chunk is None:
                logger.info("WebSocket received None chunk, ending stream for run_id: %s", run_id)
                break
            logger.info("WebSocket sending chunk: %s", chunk)
            await ws.send_json(chunk)

        # End-of-run notification to the frontend
        await ws.send_json({"status": "done", "run_id": run_id})
        logger.info("WebSocket sent 'done' status for run_id: %s", run_id)

        # Clean up the per-run queue reference on this server
        stream.discard(run_id)
        logger.info("WebSocket cleaning up and closing for run_id: %s", run_id)
        await close_ws(ws, code=1000)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for run_id: %s", run_id)
        # Keep the run/task alive for potential re-subscribe/reconnect
    except Exception as e:  # pragma: no cover - runtime errors
        logger.exception("WS error for run_id: %s", run_id)
        await close_ws(ws, code=1011, reason=str(e))
    finally:
        # Purge finished tasks (don't kill running tasks on disconnect)
        for cid, task in list(RUNNING_TASKS.items()):
            if task.done():
                del RUNNING_TASKS[cid]
