# api/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from orchestrator.core_loop import graph, LoopState, Memory
from orchestrator import crud
from uuid import uuid4

router = APIRouter()

@router.websocket("/stream")
async def stream_chat(ws: WebSocket):
    await ws.accept()
    run_id = None
    try:
        payload = await ws.receive_json()
        objective = payload.get("objective", "")
        project_id = payload.get("project_id")
        run_id = str(uuid4())
        crud.create_run(run_id, project_id)

        state = LoopState(objective=objective, project_id=project_id, run_id=run_id, mem_obj=Memory())

        await ws.send_json({"run_id": run_id})
        async for chunk in graph.astream(state):
            await ws.send_json(jsonable_encoder(chunk))

        crud.finish_run(run_id, "success")
        await ws.close(code=1000)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        if run_id:
            crud.finish_run(run_id, "failed", str(e))
        msg = (str(e) or "internal error")[:120]
        await ws.close(code=1011, reason=msg)
