from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.ws import router as ws_router
from orchestrator.core_loop import graph, LoopState, Memory
from orchestrator import crud, models

app = FastAPI()

@app.on_event("startup")
def startup():
    crud.init_db()

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
    project_id = payload.get("project_id")
    if project_id is None:
        raise HTTPException(status_code=400, detail="project_id required")
    state = LoopState(objective=objective, mem_obj=Memory(project_id))
    final = graph.invoke(state)
    return final["render"]  # html + summary


@app.get("/projects")
async def list_projects():
    return crud.get_projects()


@app.post("/projects")
async def create_project(project: models.ProjectCreate):
    return crud.create_project(project)


@app.get("/projects/{project_id}")
async def get_project(project_id: int):
    project = crud.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404)
    return project


@app.put("/projects/{project_id}")
async def update_project(project_id: int, project: models.ProjectCreate):
    updated = crud.update_project(project_id, project)
    if not updated:
        raise HTTPException(status_code=404)
    return updated


@app.delete("/projects/{project_id}")
async def delete_project(project_id: int):
    if not crud.delete_project(project_id):
        raise HTTPException(status_code=404)
    return {"status": "deleted"}


@app.get("/items")
async def list_items(project_id: int, limit: int = 10):
    mem = Memory(project_id)
    items = mem.fetch(limit)
    return [{"role": r, "content": c} for r, c in items]


@app.get("/items/{item_id}")
async def get_item(item_id: int, project_id: int):
    mem = Memory(project_id)
    item = mem.fetch_item(item_id)
    if not item:
        raise HTTPException(status_code=404)
    return item
