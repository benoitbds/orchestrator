# api/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from orchestrator.core_loop import graph, LoopState, Memory

router = APIRouter()

@router.websocket("/stream")
async def stream_chat(ws: WebSocket):
    await ws.accept()
    try:
        # 1) Attend le 1er message JSON : {"objective": "..."}
        payload = await ws.receive_json()
        objective = payload.get("objective", "")
        project_id = payload.get("project_id")
        if project_id is None:
            await ws.close(code=1008, reason="project_id required")
            return

        # 2) Prépare l’état initial
        state = LoopState(objective=objective, mem_obj=Memory(project_id))

        # 3) Stream LangGraph
        async for chunk in graph.astream(state):
            # chunk est un dict {"node": "plan", "state": {...}}
            await ws.send_json(jsonable_encoder(chunk))

        await ws.close(code=1000)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        msg = (str(e) or "internal error")[:120]
        await ws.close(code=1011, reason=msg)
