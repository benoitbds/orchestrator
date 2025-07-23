from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.ws import router as ws_router
from orchestrator.core_loop import graph, LoopState, Memory
from orchestrator import crud
from orchestrator.models import Item, ItemCreate, ItemUpdate
from fastapi import HTTPException, Query

app = FastAPI()
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


# -------------------- Items --------------------

@app.get("/items", response_model=list[Item])
async def list_items(
    project_id: int = Query(...),
    type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return crud.get_items(project_id=project_id, type=type, limit=limit, offset=offset)


@app.post("/items", response_model=Item, status_code=201)
async def create_item(item: ItemCreate):
    if item.parent_id is not None:
        parent = crud.get_item(item.parent_id)
        if not parent or parent.project_id != item.project_id:
            raise HTTPException(status_code=400, detail="invalid parent_id")
        if parent.type != "folder":
            raise HTTPException(status_code=400, detail="parent must be folder")
    return crud.create_item(item)


@app.get("/items/{item_id}", response_model=Item)
async def read_item(item_id: int, project_id: int | None = Query(None)):
    item = crud.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404)
    if project_id is not None and item.project_id != project_id:
        raise HTTPException(status_code=404)
    return item


@app.patch("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, payload: ItemUpdate):
    item = crud.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404)
    data = payload.model_dump(exclude_unset=True)
    if "parent_id" in data and data["parent_id"] is not None:
        new_parent = crud.get_item(data["parent_id"])
        if not new_parent or new_parent.project_id != item.project_id:
            raise HTTPException(status_code=400, detail="invalid parent_id")
        if new_parent.type != "folder" or new_parent.id == item_id:
            raise HTTPException(status_code=400, detail="invalid hierarchy")
        # check not moving under its descendant
        current = new_parent
        while current.parent_id is not None:
            if current.parent_id == item_id:
                raise HTTPException(status_code=400, detail="cycle detected")
            current = crud.get_item(current.parent_id)
            if current is None:
                break
    return crud.update_item(item_id, ItemUpdate(**data))


@app.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    item = crud.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404)
    if crud.item_has_children(item_id):
        raise HTTPException(status_code=400, detail="item has children")
    crud.delete_item(item_id)
    return None
