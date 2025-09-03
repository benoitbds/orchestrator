import os
import json
import asyncio
import logging
from datetime import datetime
from importlib import metadata
from uuid import uuid4
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from fastapi import File, FastAPI, HTTPException, Query, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
from api.ws import router as ws_router
from pydantic import BaseModel

from orchestrator import crud, stream
from orchestrator.core_loop import run_chat_tools
from agents import writer, planner
from orchestrator.models import (
    ProjectCreate,
    BacklogItemCreate,
    BacklogItemUpdate,
    BacklogItem,
    DocumentOut,
    RunDetail,
    RunSummary,
    TimelineEvent,
    RunCost,
    FeatureCreate,
    EpicCreate,
    CapabilityCreate,
    USCreate,
    UCCreate,
    LayoutUpdate,
)
import httpx
from agents.embeddings import chunk_text, embed_texts
from orchestrator.logging_utils import JSONLHandler


def setup_logging(log_dir: str = "logs") -> None:
    level_name = os.getenv("LOGLEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # If no handler yet, add a simple StreamHandler
    if not root.handlers:
        h = logging.StreamHandler()
        h.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        root.addHandler(h)

    if not any(isinstance(h, JSONLHandler) for h in root.handlers):
        root.addHandler(JSONLHandler(log_dir))


async def _no_aclose(self):
    """Stub aclose to keep AsyncClient usable after context manager in tests."""
    pass


httpx.AsyncClient.aclose = _no_aclose


async def _no_aexit(self, exc_type=None, exc_value=None, traceback=None):
    pass


httpx.AsyncClient.__aexit__ = _no_aexit

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()
crud.init_db()


class RunAgentPayload(BaseModel):
    project_id: int
    objective: str


@app.post("/agent/run")
async def run_agent(payload: RunAgentPayload):
    project = crud.get_project(payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    async def _bg() -> None:
        try:
            await planner.run_objective(
                project_id=payload.project_id, objective=payload.objective
            )
        except Exception as e:  # pragma: no cover - unexpected runtime errors
            logger.warning("planner failed: %s", e)

    asyncio.create_task(_bg())
    # For backward compatibility the endpoint simply acknowledges the request.
    return {"ok": True}


@app.on_event("startup")
def startup_event():
    crud.init_db()

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.1.93:3000",
]

# Allow configured origins and fall back to accepting any HTTP(S) origin for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)

@app.middleware("http")
async def log_origin(request, call_next):
    origin = request.headers.get("origin")
    path = request.url.path
    logging.getLogger("cors").debug("Origin %r -> %s", origin, path)
    response = await call_next(request)
    return response


try:
    __version__ = metadata.version("orchestrator")
except metadata.PackageNotFoundError:  # pragma: no cover - fallback when not installed
    __version__ = "0.1.0"


@app.get("/health")
async def health():
    """Basic health-check endpoint."""
    return {
        "status": "ok",
        "service": "orchestrator",
        "version": __version__,
        "time": datetime.utcnow().isoformat(),
    }

@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.post("/chat")
async def chat(payload: dict) -> dict:
    """Handle a chat objective and return the run result."""
    # This endpoint is deprecated in favor of /agent/run + /runs/{run_id}
    raise HTTPException(status_code=410, detail="This endpoint is deprecated. Use /agent/run instead.")


@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    run = crud.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@app.get("/runs/{run_id}/steps")
async def get_run_steps(run_id: str, limit: int = Query(200, ge=1, le=1000)):
    """Get conversation steps/logs for a run."""
    run = crud.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    steps = crud.get_run_steps(run_id, limit)
    return {"run_id": run_id, "steps": steps, "total_steps": len(steps)}


@app.get("/runs/{run_id}/timeline", response_model=list[TimelineEvent])
async def get_run_timeline(
    run_id: str,
    limit: int = Query(1000, ge=1, le=1000),
    cursor: str | None = None,
):
    run = crud.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return crud.get_run_timeline(run_id, limit=limit, cursor=cursor)


@app.get("/runs/{run_id}/cost", response_model=RunCost)
async def get_run_cost(run_id: str):
    run = crud.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return crud.get_run_cost(run_id)


@app.get("/runs", response_model=list[RunSummary])
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


# ---- Document endpoints ----


@app.post(
    "/projects/{project_id}/documents",
    response_model=DocumentOut,
    status_code=201,
)
async def upload_document(project_id: int, file: UploadFile = File(...)):
    """Upload a document for a project."""

    if not crud.get_project(project_id):
        raise HTTPException(status_code=404, detail="project not found")

    content_bytes = await file.read()
    
    # Extract text from document using appropriate parser
    from orchestrator.doc_processing import extract_text_from_file, DocumentParsingError
    
    try:
        content_text = extract_text_from_file(content_bytes, file.filename)
    except DocumentParsingError as e:
        raise HTTPException(status_code=422, detail=f"Document parsing failed: {str(e)}")

    # Create the document first
    document = crud.create_document(project_id, file.filename, content_text, None)

    chunks = chunk_text(content_text, target_tokens=400, overlap_tokens=60)
    try:
        embeddings = await embed_texts(chunks)
    except Exception as e:  # pragma: no cover - unexpected
        logger.warning("Failed to embed document %s: %s", document.id, e)
        embeddings = [[] for _ in chunks]

    payload = [
        (i, chunk, embeddings[i] if i < len(embeddings) else [])
        for i, chunk in enumerate(chunks)
    ]
    if payload:
        crud.upsert_document_chunks(document.id, payload)

    return document


@app.get(
    "/projects/{project_id}/documents",
    response_model=list[DocumentOut],
)
async def list_documents(project_id: int):
    """List documents for a project."""

    if not crud.get_project(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    return crud.get_documents(project_id)


@app.get("/documents/{doc_id}/content")
async def get_document_content(doc_id: int):
    """Return the stored content of a document."""

    doc = crud.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    return Response(doc.get("content") or "", media_type="text/plain")


@app.get("/documents/{doc_id}/chunks")
async def get_document_chunks(doc_id: int):
    """Get all chunks for a specific document."""
    
    # Verify document exists
    doc = crud.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")

    chunks = crud.get_document_chunks(doc_id)
    return chunks


@app.delete("/documents/{doc_id}")
def delete_document_api(doc_id: int):
    doc = crud.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    crud.delete_document_chunks(doc_id)

    fp = doc.get("filepath")
    if fp:
        try:
            os.remove(fp)
        except FileNotFoundError:
            pass

    ok = crud.delete_document(doc_id)
    return {"ok": bool(ok)}


@app.post("/projects/{project_id}/search")
async def search_documents(
    project_id: int,
    query: dict
):
    """Search for similar document chunks using semantic search."""
    
    if not crud.get_project(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    
    query_text = query.get("query", "")
    if not query_text:
        raise HTTPException(status_code=400, detail="Query text is required")
    
    limit = query.get("limit", 5)
    similarity_threshold = query.get("similarity_threshold", 0.3)
    
    try:
        from orchestrator.embedding_service import get_embedding_service, EmbeddingError
        
        # Generate embedding for the query
        embedding_service = get_embedding_service()
        query_embedding = await embedding_service.generate_embedding(query_text)
        
        # Get all chunks for the project
        all_chunks = crud.get_all_chunks_for_project(project_id)
        
        if not all_chunks:
            return {"query": query_text, "results": [], "total_chunks": 0}
        
        # Find similar chunks
        similar_chunks = await embedding_service.find_similar_chunks(
            query_embedding=query_embedding,
            chunk_embeddings=all_chunks,
            top_k=limit,
            similarity_threshold=similarity_threshold
        )
        
        return {
            "query": query_text,
            "results": similar_chunks,
            "total_chunks": len(all_chunks),
            "similarity_threshold": similarity_threshold
        }
        
    except EmbeddingError as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {str(e)}")
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/projects/{project_id}/layout")
async def get_project_layout(project_id: int):
    if not crud.get_project(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    nodes = crud.get_layout(project_id)
    return {"nodes": nodes}


@app.put("/projects/{project_id}/layout")
async def put_project_layout(project_id: int, payload: LayoutUpdate):
    if not crud.get_project(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    for node in payload.nodes:
        item = crud.get_item(node.item_id)
        if not item or item.project_id != project_id:
            raise HTTPException(status_code=400, detail=f"invalid item_id {node.item_id}")
    crud.upsert_layout(project_id, [n.model_dump() for n in payload.nodes])
    return {"ok": True, "count": len(payload.nodes)}


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
