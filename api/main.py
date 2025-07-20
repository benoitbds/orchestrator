from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.ws import router as ws_router
from orchestrator.core_loop import graph, LoopState, Memory

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:9080",
]

# Autorise l’origine du front (dev localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)

@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.post("/chat")
async def chat(payload: dict):
    objective = payload.get("objective", "")
    state = LoopState(objective=objective, mem_obj=Memory())
    final = graph.invoke(state)
    return final["render"]  # html + summary
