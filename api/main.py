from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.ws import router as ws_router
from orchestrator.core_loop import graph, LoopState, Memory
from orchestrator import crud
from orchestrator.models import ProjectCreate, BacklogItemCreate

app = FastAPI()


@app.on_event("startup")
def startup_event():
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
    state = LoopState(objective=objective, mem_obj=Memory())
    final = graph.invoke(state)
    return final["render"]  # html + summary


# ---- Project endpoints ----
@app.get("/projects")
async def list_projects():
    return crud.get_projects()


@app.post("/projects")
async def create_project(project: ProjectCreate):
    return crud.create_project(project)


@app.put("/projects/{project_id}")
async def update_project(project_id: int, project: ProjectCreate):
    return crud.update_project(project_id, project)


@app.delete("/projects/{project_id}")
async def delete_project(project_id: int):
    return crud.delete_project(project_id)


# ---- Backlog item endpoints ----
@app.get("/projects/{project_id}/items")
async def list_items(project_id: int):
    return crud.get_items(project_id)


@app.post("/projects/{project_id}/items")
async def create_item(project_id: int, item: BacklogItemCreate):
    item.project_id = project_id
    return crud.create_item(item)


@app.put("/items/{item_id}")
async def update_item(item_id: int, item: BacklogItemCreate):
    return crud.update_item(item_id, item)


@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    return crud.delete_item(item_id)
