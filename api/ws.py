# api/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from orchestrator import stream

router = APIRouter()

@router.websocket("/stream")
async def stream_chat(ws: WebSocket):
    await ws.accept()
    try:
        payload = await ws.receive_json()
        run_id = payload.get("run_id")
        if not run_id:
            await ws.close(code=1008, reason="run_id required")
            return
        queue = stream.get(run_id)
        if queue is None:
            await ws.close(code=404, reason="unknown run")
            return
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            await ws.send_json(chunk)
        stream.discard(run_id)
        await ws.close(code=1000)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        msg = (str(e) or "internal error")[:120]
        await ws.close(code=1011, reason=msg)
