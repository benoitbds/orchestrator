from fastapi import FastAPI, HTTPException, Query
import asyncio
import threading
from fastapi.middleware.cors import CORSMiddleware
from api.ws import router as ws_router
from uuid import uuid4
from orchestrator.core_loop import graph, LoopState, Memory
from orchestrator import crud
from orchestrator.models import (
    ProjectCreate,
    BacklogItemCreate,
    BacklogItemUpdate,
    BacklogItem,
    Run,
    FeatureCreate,
)
import agents.writer as writer
import httpx


async def _no_aclose(self):
    """Stub aclose to keep AsyncClient usable after context manager in tests."""
    pass


httpx.AsyncClient.aclose = _no_aclose


async def _no_aexit(self, exc_type=None, exc_value=None, traceback=None):
    pass


httpx.AsyncClient.__aexit__ = _no_aexit

app = FastAPI()
crud.init_db()


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
    project_id = payload.get("project_id")
    run_id = str(uuid4())
    crud.create_run(run_id, project_id)
    state = LoopState(objective=objective, project_id=project_id, run_id=run_id, mem_obj=Memory())

    def _run():
        try:
            final = graph.invoke(state)
            render = final.get("render") if isinstance(final, dict) else None
            if render is None and hasattr(state, "render"):
                render = state.render
            if render is None:
                render = {"html": "<p>done</p>", "summary": "done", "artifacts": []}
            crud.finish_run(run_id, "success", render)
        except Exception as e:
            crud.finish_run(run_id, "failed", error=str(e))

    threading.Thread(target=_run, daemon=True).start()
    return {"run_id": run_id}


@app.get("/runs/{run_id}", response_model=Run)
async def read_run(run_id: str):
    run = crud.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404)
    return run


@app.get("/runs", response_model=list[Run])
async def list_runs(project_id: int | None = Query(None)):
    return crud.get_runs(project_id)



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

@app.get("/api/items", response_model=list[BacklogItem])
@app.get("/items", response_model=list[BacklogItem])
async def list_items(
    project_id: int = Query(...),
    type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return crud.get_items(project_id=project_id, type=type, limit=limit, offset=offset)


@app.post("/api/items", response_model=BacklogItem, status_code=201)
@app.post("/items", response_model=BacklogItem, status_code=201)
async def create_item(item_data: dict):
    from orchestrator.models import EpicCreate, CapabilityCreate, FeatureCreate, USCreate, UCCreate
    
    # Créer le bon modèle selon le type
    item_type = item_data.get("type")
    try:
        if item_type == "Epic":
            item = EpicCreate(**item_data)
        elif item_type == "Capability":
            item = CapabilityCreate(**item_data)
        elif item_type == "Feature":
            item = FeatureCreate(**item_data)
        elif item_type == "US":
            item = USCreate(**item_data)
        elif item_type == "UC":
            item = UCCreate(**item_data)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid type: {item_type}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    
    if item.parent_id is not None:
        parent = crud.get_item(item.parent_id)
        if not parent or parent.project_id != item.project_id:
            raise HTTPException(status_code=400, detail="invalid parent_id")
        # Vérifier la hiérarchie : Epic→Capability→Feature→US→UC
        allowed = {
            "Capability": ["Epic"], 
            "Feature": ["Epic", "Capability"], 
            "US": ["Feature"], 
            "UC": ["US"]
        }
        if item.type not in allowed or parent.type not in allowed[item.type]:
            raise HTTPException(status_code=400, detail="invalid hierarchy")
    return crud.create_item(item)


@app.post("/projects/{project_id}/items", response_model=BacklogItem)
async def create_project_item(project_id: int, item_data: dict):
    item_data["project_id"] = project_id
    return await create_item(item_data)


@app.get("/projects/{project_id}/items", response_model=list[BacklogItem])
async def list_project_items(project_id: int, type: str | None = Query(None), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    return crud.get_items(project_id=project_id, type=type, limit=limit, offset=offset)


@app.post("/api/feature_proposals", status_code=201)
async def feature_proposals(payload: dict):
    project_id = payload.get("project_id")
    parent_id = payload.get("parent_id")
    parent_title = payload.get("parent_title")
    if project_id is None or parent_id is None or parent_title is None:
        raise HTTPException(status_code=400, detail="missing fields")
    proposals = writer.make_feature_proposals(project_id, parent_id, parent_title)
    created = []
    for prop in proposals.proposals:
        item = FeatureCreate(
            title=prop.title,
            description=prop.description,
            project_id=project_id,
            parent_id=parent_id,
        )
        created.append(crud.create_item(item))
    return created


@app.get("/api/items/{item_id}", response_model=BacklogItem)
async def read_item(item_id: int):
    item = crud.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404)
    return item


@app.patch("/api/items/{item_id}", response_model=BacklogItem)
async def update_item(item_id: int, payload: BacklogItemUpdate):
    item = crud.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404)
    data = payload.model_dump(exclude_unset=True)
    if "parent_id" in data and data["parent_id"] is not None:
        new_parent = crud.get_item(data["parent_id"])
        if not new_parent or new_parent.project_id != item.project_id:
            raise HTTPException(status_code=400, detail="invalid parent_id")
        # Vérifier la hiérarchie autorisée selon le type de l'item
        allowed = {
            "Capability": ["Epic"], 
            "Feature": ["Epic", "Capability"], 
            "US": ["Feature"], 
            "UC": ["US"]
        }
        # pas de parent autorisé pour les Epics
        if item.type not in allowed or new_parent.type not in allowed[item.type] or new_parent.id == item_id:
            raise HTTPException(status_code=400, detail="invalid hierarchy")
        # détecter les cycles
        current = new_parent
        while current.parent_id is not None:
            if current.parent_id == item_id:
                raise HTTPException(status_code=400, detail="cycle detected")
            current = crud.get_item(current.parent_id)
            if current is None:
                break
    return crud.update_item(item_id, BacklogItemUpdate(**data))


@app.delete("/api/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    item = crud.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404)
    # suppression en cascade des descendants
    crud.delete_item(item_id)
    return None
