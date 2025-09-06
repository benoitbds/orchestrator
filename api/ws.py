from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

import logging
from orchestrator.core_loop import run_chat_tools
from orchestrator import crud, stream

router = APIRouter()
logger = logging.getLogger(__name__)


async def close_ws(ws: WebSocket, code: int, reason: str | None = None) -> None:
    """Close websocket if still connected."""
    if ws.client_state == WebSocketState.CONNECTED:
        await ws.close(code=code, reason=reason)


@router.websocket("/stream")
async def stream_chat(ws: WebSocket):
    await ws.accept()
    run_id: str | None = None
    try:
        payload = await ws.receive_json()
        action = payload.get("action", "start")  # "start" or "subscribe"
        run_id = payload.get("run_id")
        objective = payload.get("objective")
        project_id = payload.get("project_id")
        request_id = payload.get("request_id")
        
        if action == "subscribe":
            # Subscribe-only mode: just stream events for existing run
            if not run_id:
                await close_ws(ws, code=1008, reason="run_id required for subscribe")
                return
                
            # Check if run exists
            run = crud.get_run(run_id)
            if not run:
                await close_ws(ws, code=4404, reason="run not found")
                return
            
            # Register for event streaming
            from orchestrator.events import register_stream
            queue = register_stream(run_id)
            await ws.send_json({"run_id": run_id, "status": "subscribed"})
            
        elif action == "start":
            # Legacy mode: start new run or continue existing
            if run_id:
                queue = stream.get(run_id)
                if queue is None:
                    await close_ws(ws, code=4404, reason="unknown run")
                    return
                # discard existing queued steps so only fresh ones are sent
                drained_done = False
                try:
                    while True:
                        item = queue.get_nowait()
                        if item is None:
                            drained_done = True
                            break
                except asyncio.QueueEmpty:
                    pass
                if drained_done:
                    await ws.send_json({"status": "done", "run_id": run_id})
                    stream.discard(run_id)
                    await close_ws(ws, code=1000)
                    return
            else:
                if not objective:
                    await close_ws(ws, code=1008, reason="objective required")
                    return
                
                # Check for existing run with same request_id
                if request_id:
                    existing_run = crud.find_run_by_request_id(request_id)
                    if existing_run and (existing_run["status"] == "running" or existing_run.get("tool_phase")):
                        # Use existing run instead of creating new one
                        run_id = existing_run["run_id"]
                        from orchestrator.events import register_stream
                        queue = register_stream(run_id)
                        await ws.send_json({"run_id": run_id, "status": "existing"})
                    else:
                        # Create new run
                        run_id = str(uuid4())
                        crud.create_run(run_id, objective, project_id, request_id)
                        queue = stream.register(run_id)
                        await ws.send_json({"run_id": run_id, "status": "started"})

                        # Start events tracking
                        from orchestrator.events import start_run
                        start_run(run_id)

                        async def runner() -> None:
                            try:
                                await run_chat_tools(objective, project_id, run_id)
                            except Exception as exc:  # pragma: no cover - unexpected errors
                                crud.finish_run(run_id, "", str(exc))
                            finally:
                                stream.close(run_id)

                        asyncio.create_task(runner())
                else:
                    # No request_id, create new run
                    run_id = str(uuid4())
                    crud.create_run(run_id, objective, project_id, request_id)
                    queue = stream.register(run_id)
                    await ws.send_json({"run_id": run_id, "status": "started"})

                    # Start events tracking
                    from orchestrator.events import start_run
                    start_run(run_id)

                    async def runner() -> None:
                        try:
                            await run_chat_tools(objective, project_id, run_id)
                        except Exception as exc:  # pragma: no cover - unexpected errors
                            crud.finish_run(run_id, "", str(exc))
                        finally:
                            stream.close(run_id)

                    asyncio.create_task(runner())

        else:
            await close_ws(ws, code=1008, reason="invalid action")
            return

        # Stream events from the queue
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            await ws.send_json(chunk)
        await ws.send_json({"status": "done", "run_id": run_id})
        
        # Clean up
        from orchestrator.events import unregister_stream
        unregister_stream(run_id)
        stream.discard(run_id)
        await close_ws(ws, code=1000)
        
    except WebSocketDisconnect:
        if run_id:
            from orchestrator.events import unregister_stream
            unregister_stream(run_id)
            stream.discard(run_id)
    except Exception as e:  # pragma: no cover - runtime errors
        logger.exception("WS error")
        await close_ws(ws, code=1011, reason=str(e))
