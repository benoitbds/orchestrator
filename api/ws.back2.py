from __future__ import annotations

import asyncio
from uuid import uuid4
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

import logging
from orchestrator.core_loop import run_chat_tools
from orchestrator import crud, stream
from orchestrator.run_registry import get_or_create_run

router = APIRouter()
logger = logging.getLogger(__name__)

# Track running tasks to cancel them when needed
RUNNING_TASKS: Dict[str, asyncio.Task] = {}


async def close_ws(ws: WebSocket, code: int, reason: str | None = None) -> None:
    """Close websocket if still connected."""
    if ws.client_state == WebSocketState.CONNECTED:
        await ws.close(code=code, reason=reason)


@router.websocket("/stream")
async def stream_chat(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket connection accepted")
    run_id: str | None = None
    queue: asyncio.Queue | None = None

    try:
        logger.info("WebSocket waiting for JSON payload...")
        payload = await ws.receive_json()
        logger.info("WebSocket received payload: %s", payload)

        action = payload.get("action", "start")  # "start" or "subscribe"
        passed_run_id = payload.get("run_id")
        objective = payload.get("objective")
        project_id = payload.get("project_id")
        client_id = (
            ws.headers.get("x-client-session-id")
            or payload.get("client_session_id")
            or payload.get("temp_run_id")
            or str(uuid4())
        )

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

            # Register to the stream for this run (do not start a new run)
            queue = stream.get(run_id)
            if queue is None:
                queue = stream.register(run_id)

            await ws.send_json({"run_id": run_id, "status": "subscribed"})

        # ========
        # START
        # ========
        elif action == "start":
            entry, created = get_or_create_run(client_id, project_id, objective, passed_run_id)
            if not entry:
                await close_ws(ws, code=1008, reason="objective or run_id required")
                return

            run_id = entry["run_id"]

            # --- Run déjà existant ---
            if not created:
                # Si déjà terminé, renvoyer "done" immédiatement
                if entry.get("status") == "done":
                    await ws.send_json({"status": "done", "run_id": run_id})
                    await close_ws(ws, code=1000)
                    return

                queue = stream.get(run_id)
                if queue is None:
                    # Run pré-créé (par HTTP) mais non démarré : on le lance maintenant
                    run = crud.get_run(run_id)
                    if run and run.get("status") != "done":
                        queue = stream.register(run_id)
                        await ws.send_json({"run_id": run_id, "status": "started"})

                        async def runner() -> None:
                            try:
                                await run_chat_tools(
                                    objective or run["objective"],
                                    project_id or run["project_id"],
                                    run_id,
                                )
                            except Exception as exc:
                                crud.finish_run(run_id, "", str(exc))
                            finally:
                                stream.close(run_id)

                        asyncio.create_task(runner())
                    else:
                        await close_ws(ws, code=4404, reason="unknown run")
                        return
                else:
                    # Run déjà en cours : signaler l'existence
                    await ws.send_json({"run_id": run_id, "status": "existing"})

            # --- Nouveau run ---
            else:
                # Consigner en base puis enregistrer la stream-queue
                crud.create_run(run_id, objective, project_id, None)
                queue = stream.register(run_id)
                await ws.send_json({"run_id": run_id, "status": "started"})

                # Annuler un éventuel run en cours pour le même client
                if client_id in RUNNING_TASKS:
                    old_task = RUNNING_TASKS[client_id]
                    if not old_task.done():
                        logger.info("Cancelling existing task for client_id: %s", client_id)
                        old_task.cancel()
                        try:
                            await old_task
                        except asyncio.CancelledError:
                            pass

                async def runner() -> None:
                    try:
                        await run_chat_tools(objective, project_id, run_id)
                    except asyncio.CancelledError:
                        logger.info("Task cancelled for run_id: %s", run_id)
                        raise
                    except Exception as exc:  # pragma: no cover - unexpected errors
                        crud.finish_run(run_id, "", str(exc))
                    finally:
                        stream.close(run_id)
                        # Remove from running tasks when done
                        current = asyncio.current_task()
                        if current is not None and RUNNING_TASKS.get(client_id) is current:
                            del RUNNING_TASKS[client_id]

                task = asyncio.create_task(runner())
                RUNNING_TASKS[client_id] = task

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

        # Fin du run : notifier le front
        await ws.send_json({"status": "done", "run_id": run_id})
        logger.info("WebSocket sent 'done' status for run_id: %s", run_id)

        # Nettoyage
        stream.discard(run_id)
        logger.info("WebSocket cleaning up and closing for run_id: %s", run_id)
        await close_ws(ws, code=1000)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for run_id: %s", run_id)
        # On garde l'état du run pour une éventuelle reconnexion
        pass
    except Exception as e:  # pragma: no cover - runtime errors
        logger.exception("WS error for run_id: %s", run_id)
        await close_ws(ws, code=1011, reason=str(e))
    finally:
        # Purger les tasks terminées
        for cid, task in list(RUNNING_TASKS.items()):
            if task.done():
                del RUNNING_TASKS[cid]
