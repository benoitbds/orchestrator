from fastapi import FastAPI
from orchestrator.core_loop import graph, LoopState, Memory

app = FastAPI()

@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.post("/chat")
async def chat(payload: dict):
    objective = payload.get("objective", "")
    state = LoopState(objective=objective, mem_obj=Memory())
    final = graph.invoke(state)
    return final["render"]  # html + summary
