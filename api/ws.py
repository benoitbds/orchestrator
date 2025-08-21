from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from orchestrator.core_loop import graph, LoopState, Memory
from orchestrator import crud, stream

router = APIRouter()


@router.websocket("/stream")
async def stream_chat(ws: WebSocket):
    await ws.accept()
    run_id: str | None = None
    try:
        payload = await ws.receive_json()
        run_id = payload.get("run_id")
        objective = payload.get("objective")
        project_id = payload.get("project_id")
        loop = asyncio.get_event_loop()

        if run_id:
            queue = stream.get(run_id)
            if queue is None:
                await ws.close(code=404, reason="unknown run")
                return
            # discard existing queued steps so only fresh ones are sent
            try:
                while True:
                    queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        else:
            if not objective:
                await ws.close(code=1008, reason="objective required")
                return
            run_id = str(uuid4())
            crud.create_run(run_id, objective, project_id)
            queue = stream.register(run_id, loop)
            state = LoopState(
                objective=objective,
                project_id=project_id,
                run_id=run_id,
                mem_obj=Memory(),
            )
            await ws.send_json({"run_id": run_id, "status": "started"})

            async def runner() -> None:
                try:
                    async for _ in graph.astream(state):
                        pass
                    render = getattr(state, "render", None) or {
                        "html": "",
                        "summary": "",
                    }
                    crud.finish_run(run_id, render.get("html", ""), render.get("summary", ""))
                except Exception as exc:  # pragma: no cover - unexpected errors
                    crud.finish_run(run_id, "", str(exc))
                finally:
                    stream.close(run_id)

            asyncio.create_task(runner())

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            await ws.send_json(chunk)
        await ws.send_json({"status": "done", "run_id": run_id})
        stream.discard(run_id)
        await ws.close(code=1000)
    except WebSocketDisconnect:
        if run_id:
            stream.discard(run_id)
    except Exception as e:  # pragma: no cover - runtime errors
        msg = (str(e) or "internal error")[:120]
        await ws.close(code=1011, reason=msg)
