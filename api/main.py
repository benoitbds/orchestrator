import os
import asyncio
import logging
from datetime import datetime
from importlib import metadata
from uuid import uuid4

import httpx
import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv
from fastapi import File, FastAPI, HTTPException, Query, UploadFile, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal

from api.ws import router as ws_router
from backend.app.security import get_current_user_optional
from backend.app.routes.projects import router as project_router

from orchestrator import crud
from orchestrator.core_loop import run_chat_tools
from agents import writer
from orchestrator.models import (
    ProjectCreate,
    BacklogItemUpdate,
    BacklogItem,
    DocumentOut,
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
from agents.embeddings import chunk_text, embed_texts
from orchestrator.logging_utils import JSONLHandler

# Load environment variables first
load_dotenv()  # Load root .env
load_dotenv("backend/.env")  # Also load backend-specific Firebase config


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


class ValidateBody(BaseModel):
    fields: list[str] | None = None


class BulkValidateBody(BaseModel):
    ids: list[int]

cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
if cred_path and not firebase_admin._apps:
    try:
        if os.path.exists(cred_path):
            firebase_admin.initialize_app(credentials.Certificate(cred_path))
            logger.info(f"Firebase initialized with service account: {cred_path}")
        else:
            logger.warning(f"Firebase service account file not found: {cred_path}")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
else:
    logger.warning("FIREBASE_SERVICE_ACCOUNT_PATH not set or Firebase already initialized")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://agent4ba.baq.ovh"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

crud.init_db()


class RunAgentPayload(BaseModel):
    project_id: int
    objective: str


@app.post("/agent/run")
async def run_agent(payload: RunAgentPayload, user=Depends(get_current_user_optional)):
    project = crud.get_project_for_user(payload.project_id, user["uid"])
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate run_id upfront to return it immediately
    from uuid import uuid4
    run_id = str(uuid4())
    
    async def _bg() -> None:
        try:
            # Create the run first
            crud.create_run(run_id, payload.objective, payload.project_id)
            # Then execute it
            from orchestrator.core_loop import run_chat_tools
            await run_chat_tools(payload.objective, payload.project_id, run_id)
        except Exception as e:  # pragma: no cover - unexpected runtime errors
            logger.warning("planner failed: %s", e)

    asyncio.create_task(_bg())
    return {"ok": True, "run_id": run_id}


@app.on_event("startup")
def startup_event():
    crud.init_db()
    # Also initialize the new SQLModel storage system
    from orchestrator.storage.db import init_db
    init_db()

# Include websocket routes after middleware setup
app.include_router(ws_router)
app.include_router(project_router)

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
    # Check if run exists in the new SQLModel storage
    from orchestrator.storage.db import get_session
    from orchestrator.storage.models import Run
    from orchestrator.storage.services import get_run_timeline as get_timeline_sqlmodel
    from sqlmodel import select
    
    with get_session() as session:
        run = session.exec(select(Run).where(Run.id == run_id)).first()
        if not run:
            # Fallback to old system for backward compatibility
            old_run = crud.get_run(run_id)
            if not old_run:
                raise HTTPException(status_code=404, detail="Run not found")
            return crud.get_run_timeline(run_id, limit=limit, cursor=cursor)
        
        # Use new SQLModel storage system
        events = get_timeline_sqlmodel(run_id, limit=limit, session=session)
        # Convert datetime objects to ISO format for JSON serialization
        for event in events:
            event["ts"] = event["ts"].isoformat()
        return events


@app.get("/runs/{run_id}/cost", response_model=RunCost)
async def get_run_cost(run_id: str):
    # Check if run exists in the new SQLModel storage
    from orchestrator.storage.db import get_session
    from orchestrator.storage.models import Run
    from orchestrator.storage.services import get_run_cost as get_cost_sqlmodel
    from sqlmodel import select
    
    with get_session() as session:
        run = session.exec(select(Run).where(Run.id == run_id)).first()
        if not run:
            # Fallback to old system for backward compatibility
            old_run = crud.get_run(run_id)
            if not old_run:
                raise HTTPException(status_code=404, detail="Run not found")
            return crud.get_run_cost(run_id)
        
        # Use new SQLModel storage system
        return get_cost_sqlmodel(run_id, session=session)


@app.get("/runs", response_model=list[RunSummary])
async def list_runs(
    project_id: int | None = Query(None), 
    user_uid: str | None = Query(None),
    current_user: dict = Depends(get_current_user_optional)
):
    # If no user_uid provided, default to current user's conversations
    if user_uid is None:
        user_uid = current_user.get("uid")
    
    return crud.get_runs(project_id, user_uid)


@app.get("/runs/{run_id}/events")
async def get_run_events(run_id: str, since: int | None = Query(None)):
    """Get structured events for a run, optionally since a sequence number."""
    from orchestrator.events import get_events, get_events_from_db
    
    # Check if run exists
    run = crud.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Try to get events from memory buffer first
    events = get_events(run_id, since)
    
    # If buffer is empty or incomplete, fall back to database
    if not events or (since is not None and len(events) == 0):
        events = get_events_from_db(run_id, since)
    
    return {"events": events}


@app.post("/agent/run_chat_tools")
async def create_run_with_idempotency(
    payload: dict = {"objective": "string", "project_id": None, "request_id": None},
    current_user: dict = Depends(get_current_user_optional)
):
    """Create a new run with request-based idempotency."""
    from orchestrator.events import start_run
    
    objective = payload.get("objective")
    project_id = payload.get("project_id")
    request_id = payload.get("request_id")
    user_uid = current_user.get("uid")
    
    if not objective:
        raise HTTPException(status_code=400, detail="Objective is required")
    
    # Check for existing run with same request_id
    if request_id:
        existing_run = crud.find_run_by_request_id(request_id)
        if existing_run:
            # Return existing run if it's still running or in tool phase
            if existing_run["status"] == "running" or existing_run.get("tool_phase"):
                return {"run_id": existing_run["run_id"], "status": "existing"}
    
    # Create new run
    run_id = str(uuid4())
    crud.create_run(run_id, objective, project_id, request_id, user_uid)
    start_run(run_id)
    
    # Start the agent in the background
    async def runner():
        try:
            await run_chat_tools(objective, project_id, run_id)
        except Exception as exc:
            crud.finish_run(run_id, "", str(exc))
    
    asyncio.create_task(runner())
    
    return {"run_id": run_id, "status": "started"}


# ---- Project endpoints ----
@app.post("/projects")
async def create_project(project: ProjectCreate, user=Depends(get_current_user_optional)):
    return crud.create_project(project, user_uid=user["uid"])


@app.put("/projects/{project_id}")
async def update_project(project_id: int, project: ProjectCreate, user=Depends(get_current_user_optional)):
    # Verify user owns this project
    existing_project = crud.get_project_for_user(project_id, user["uid"])
    if not existing_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return crud.update_project(project_id, project)


@app.delete("/projects/{project_id}")
async def delete_project(project_id: int, user=Depends(get_current_user_optional)):
    # Verify user owns this project
    existing_project = crud.get_project_for_user(project_id, user["uid"])
    if not existing_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return crud.delete_project(project_id)


# ---- Document endpoints ----


@app.post(
    "/projects/{project_id}/documents",
    response_model=DocumentOut,
    status_code=201,
)
async def upload_document(project_id: int, file: UploadFile = File(...), user=Depends(get_current_user_optional)):
    """Upload a document for a project."""

    if not crud.get_project_for_user(project_id, user["uid"]):
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

    return document


@app.get(
    "/projects/{project_id}/documents",
    response_model=list[DocumentOut],
)
async def list_documents(project_id: int, user=Depends(get_current_user_optional)):
    """List documents for a project."""

    if not crud.get_project_for_user(project_id, user["uid"]):
        raise HTTPException(status_code=404, detail="project not found")
    return crud.get_documents(project_id)


@app.get("/documents", response_model=list[DocumentOut])
async def list_documents_v2(project_id: int = Query(..., ge=1), user=Depends(get_current_user_optional)):
    """List documents for a project (v2) with status metadata."""
    if not crud.get_project_for_user(project_id, user["uid"]):
        raise HTTPException(status_code=404, detail="project not found")
    return crud.get_documents(project_id)


@app.post("/documents/{doc_id}/analyze", response_model=DocumentOut)
async def analyze_document(doc_id: int, user=Depends(get_current_user_optional)):
    """Chunk and embed a document, updating its status lifecycle."""
    doc = crud.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    if not crud.get_project_for_user(doc["project_id"], user["uid"]):
        raise HTTPException(status_code=404, detail="project not found")

    crud.update_document_status(doc_id, "ANALYZING", None)
    content = (doc.get("content") or "").strip()
    if not content:
        crud.update_document_status(doc_id, "ERROR", {"error": "Document content is empty"})
        raise HTTPException(status_code=400, detail="Document content is empty")

    try:
        chunks = chunk_text(content, target_tokens=400, overlap_tokens=60)
        if not chunks:
            crud.update_document_status(doc_id, "ERROR", {"error": "No analyzable content"})
            raise HTTPException(status_code=400, detail="Document contains no analyzable content")

        embeddings = await embed_texts(chunks)
        if len(embeddings) < len(chunks):
            embeddings.extend([[] for _ in range(len(chunks) - len(embeddings))])

        non_null_embeddings = sum(1 for emb in embeddings if emb)
        if non_null_embeddings == 0:
            crud.update_document_status(
                doc_id,
                "ERROR",
                {"error": "Embedding generation failed"},
            )
            raise HTTPException(status_code=500, detail="Document analysis failed")

        payload = [
            (i, chunk, embeddings[i])
            for i, chunk in enumerate(chunks)
        ]

        crud.delete_document_chunks(doc_id)
        if payload:
            crud.upsert_document_chunks(doc_id, payload)

        total_chunks, stored_with_embeddings = crud.document_chunk_stats(doc_id)
        logger.info(
            "Indexed %s chunks, %s with embeddings (doc_id=%s)",
            total_chunks,
            stored_with_embeddings,
            doc_id,
        )
        crud.update_document_status(doc_id, "ANALYZED", {"chunk_count": total_chunks})
        updated = crud.get_document(doc_id)
        return DocumentOut(**updated)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - unexpected runtime error
        logger.exception("Document analysis failed for doc_id=%s", doc_id, exc_info=exc)
        crud.update_document_status(doc_id, "ERROR", {"error": str(exc)})
        raise HTTPException(status_code=500, detail="Document analysis failed")


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
    query: dict,
    user=Depends(get_current_user_optional)
):
    """Search for similar document chunks using semantic search."""
    
    if not crud.get_project_for_user(project_id, user["uid"]):
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
async def get_project_layout(project_id: int, user=Depends(get_current_user_optional)):
    if not crud.get_project_for_user(project_id, user["uid"]):
        raise HTTPException(status_code=404, detail="project not found")
    nodes = crud.get_layout(project_id)
    return {"nodes": nodes}


@app.put("/projects/{project_id}/layout")
async def put_project_layout(project_id: int, payload: LayoutUpdate, user=Depends(get_current_user_optional)):
    if not crud.get_project_for_user(project_id, user["uid"]):
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
    review: Literal["pending", "approved", "all"] = Query("all"),
):
    review_filter = None if review == "all" else review
    return crud.get_items(
        project_id=project_id,
        type=type,
        limit=limit,
        offset=offset,
        review=review_filter,
    )


@app.post("/api/items", response_model=BacklogItem, status_code=201)
@app.post("/items", response_model=BacklogItem, status_code=201)
async def create_item(item_data: dict):
    
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
async def list_project_items(
    project_id: int,
    type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    review: Literal["pending", "approved", "all"] = Query("all"),
):
    review_filter = None if review == "all" else review
    return crud.get_items(
        project_id=project_id,
        type=type,
        limit=limit,
        offset=offset,
        review=review_filter,
    )


@app.post("/items/{item_id}/validate", response_model=BacklogItem)
async def validate_item_endpoint(item_id: int, body: ValidateBody, user=Depends(get_current_user_optional)):
    if not user:
        raise HTTPException(status_code=401, detail="authentication required")
    item = crud.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="item not found")
    user_uid = user.get("uid") or user.get("email")
    updated = crud.validate_item(item_id, user_uid)
    if not updated:
        raise HTTPException(status_code=404, detail="item not found")
    return updated


@app.post("/items/validate", response_model=list[BacklogItem])
async def validate_items_endpoint(payload: BulkValidateBody, user=Depends(get_current_user_optional)):
    if not user:
        raise HTTPException(status_code=401, detail="authentication required")
    if not payload.ids:
        return []
    user_uid = user.get("uid") or user.get("email")
    updated = crud.validate_items(payload.ids, user_uid)
    return updated


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
    updated = crud.update_item(item_id, BacklogItemUpdate(**data))
    updated = crud.mark_item_user_touch(item_id) if updated else updated
    return updated


@app.delete("/api/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    item = crud.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404)
    # suppression en cascade des descendants
    crud.delete_item(item_id)
    return None
