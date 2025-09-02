"""Async handlers for backlog management tools."""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional
import logging

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    field_validator,
    model_validator,
    constr,
)

from orchestrator import crud
from orchestrator.prompt_loader import load_prompt
# Load environment variables
load_dotenv()
try:  # pragma: no cover - fallback if embeddings not ready
    from .embeddings import embed_text, cosine_similarity
except Exception:  # pragma: no cover
    def embed_text(text: str) -> list[float]:
        return [0.0]

    def cosine_similarity(a: List[float], b: List[float]) -> float:
        return 0.0
from orchestrator.models import (
    EpicCreate,
    CapabilityCreate,
    FeatureCreate,
    USCreate,
    UCCreate,
    BacklogItemUpdate,
)

# Logger
logger = logging.getLogger(__name__)

# Prompt templates
FEATURES_FROM_EXCERPTS_PROMPT = load_prompt("features_from_excerpts")


class GeneratedFeature(BaseModel):
    """Structured representation of a drafted Feature."""

    title: constr(max_length=120)
    objective: str
    business_value: str
    acceptance_criteria: List[str] = Field(min_length=2, max_length=4)
    parent_hint: Optional[str] = None


class GeneratedFeatures(BaseModel):
    features: List[GeneratedFeature]


class ParentRef(BaseModel):
    """Reference to a parent item by type and title."""

    type: str
    title: str


class _CreateArgs(BaseModel):
    """Arguments accepted by ``create_item_tool``.

    ``parent`` is resolved by title/type; ``parent_id`` is kept for backward
    compatibility with existing tests/tools.
    """

    title: str
    type: str
    project_id: int
    description: str | None = None
    parent_id: int | None = None
    parent: ParentRef | None = None

    @field_validator("type")
    @classmethod
    def _normalise_type(cls, v: str) -> str:
        return v.upper() if v.lower() in {"us", "uc"} else v.capitalize()

class LookupRef(BaseModel):
    """Lookup reference used when updating without explicit id."""

    type: str
    title: str
    project_id: int

    @field_validator("type")
    @classmethod
    def _normalise_type(cls, v: str) -> str:
        return v.upper() if v.lower() in {"us", "uc"} else v.capitalize()


class UpdateFields(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    parent_id: int | None = None


class _UpdateArgs(BaseModel):
    id: int | None = None
    lookup: LookupRef | None = None
    fields: UpdateFields

class _FindArgs(BaseModel):
    query: str
    project_id: int
    type: str | None = None


class _GetArgs(BaseModel):
    id: int | None = None
    type: str | None = None
    title: str | None = None
    project_id: int | None = None

    @field_validator("type")
    @classmethod
    def _normalise_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.upper() if v.lower() in {"us", "uc"} else v.capitalize()

    @model_validator(mode="after")
    def _check_one_of(cls, data: "_GetArgs") -> "_GetArgs":
        if data.id is None and not all([data.type, data.title, data.project_id]):
            raise ValueError("id or (type,title,project_id) required")
        return data


class _ListArgs(BaseModel):
    project_id: int
    type: str | None = None
    query: str | None = None
    limit: int = 100
    offset: int = 0

    @field_validator("type")
    @classmethod
    def _normalise_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.upper() if v.lower() in {"us", "uc"} else v.capitalize()


class _DeleteArgs(BaseModel):
    id: int


class _MoveArgs(BaseModel):
    id: int
    new_parent_id: int


class _SummarizeArgs(BaseModel):
    project_id: int
    depth: int = 3


class _BulkFeature(BaseModel):
    title: str
    description: str | None = None


class _BulkCreateArgs(BaseModel):
    project_id: int
    parent_id: int
    items: List[_BulkFeature]

_ALLOWED_PARENT = {
    "Capability": ["Epic"],
    "Feature": ["Epic", "Capability"],
    "US": ["Feature"],
    "UC": ["US"],
}

_MODEL_MAP = {
    "Epic": EpicCreate,
    "Capability": CapabilityCreate,
    "Feature": FeatureCreate,
    "US": USCreate,
    "UC": UCCreate,
}

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def create_item_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Validate args and create a backlog item.

    ``parent`` can be provided instead of ``parent_id`` and will be resolved by
    title and type within the given project.  When multiple matches are found,
    an ``parent_ambiguous`` error is returned so the caller can clarify.
    """

    try:
        data = _CreateArgs(**args)
        parent_id = data.parent_id
        # Resolve parent if given as reference
        if data.parent is not None:
            items = crud.get_items(data.project_id, type=data.parent.type)
            matches = [
                it for it in items if it.title.lower() == data.parent.title.lower()
            ]
            if not matches:
                return {"ok": False, "error": "parent_not_found"}
            if len(matches) > 1:
                return {"ok": False, "error": "parent_ambiguous"}
            parent_id = matches[0].id

        if parent_id is not None:
            parent = crud.get_item(parent_id)
            if not parent or parent.project_id != data.project_id:
                raise ValueError("invalid parent_id")
            allowed = _ALLOWED_PARENT.get(data.type, [])
            if parent.type not in allowed:
                raise ValueError("invalid hierarchy")

        Model = _MODEL_MAP[data.type]
        item = Model(
            title=data.title,
            description=data.description or "",
            project_id=data.project_id,
            parent_id=parent_id,
        )
        created = crud.create_item(item)
        return {
            "ok": True,
            "item_id": created.id,
            "type": created.type,
            "title": created.title,
        }
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}

async def update_item_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Validate args & existence; update item.

    Supports targeting an item either by explicit ``id`` or by a lookup
    (``type`` + ``title`` + ``project_id``).  Updates are passed through to the
    CRUD layer after validating hierarchy rules.
    """

    try:
        # Backward compatibility: allow id/fields at top-level
        if "fields" not in args:
            lookup = None
            if args.get("id") is None and {
                "type",
                "title",
                "project_id",
            }.issubset(args):
                lookup = {
                    "type": args["type"],
                    "title": args["title"],
                    "project_id": args["project_id"],
                }
                fields = {
                    k: v
                    for k, v in args.items()
                    if k not in {"id", "type", "title", "project_id", "lookup"}
                }
            else:
                fields = {
                    k: v
                    for k, v in args.items()
                    if k not in {"id", "type", "project_id", "lookup"}
                }
            args = {"id": args.get("id"), "lookup": lookup, "fields": fields}

        data = _UpdateArgs(**args)

        item_id = data.id
        if item_id is None:
            # Resolve via lookup
            items = crud.get_items(
                data.lookup.project_id, type=data.lookup.type
            )
            matches = [
                it
                for it in items
                if it.title.lower() == data.lookup.title.lower()
            ]
            if not matches:
                return {"ok": False, "error": "item_not_found"}
            if len(matches) > 1:
                return {"ok": False, "error": "item_ambiguous"}
            item_id = matches[0].id

        item = crud.get_item(item_id)
        if not item:
            raise ValueError("item not found")

        update_data = data.fields.model_dump(exclude_none=True)

        if "parent_id" in update_data:
            new_parent_id = update_data["parent_id"]
            if new_parent_id is not None:
                new_parent = crud.get_item(new_parent_id)
                if not new_parent or new_parent.project_id != item.project_id:
                    raise ValueError("invalid parent_id")
                allowed = _ALLOWED_PARENT.get(item.type, [])
                if new_parent.type not in allowed or new_parent.id == item.id:
                    raise ValueError("invalid hierarchy")
                current = new_parent
                while current.parent_id is not None:
                    if current.parent_id == item_id:
                        raise ValueError("cycle detected")
                    current = crud.get_item(current.parent_id)
                    if current is None:
                        break

        if "status" in update_data and item.type in {"US", "UC"}:
            if update_data["status"] not in {"Todo", "Doing", "Done"}:
                raise ValueError("invalid status")
        elif "status" in update_data and item.type not in {"US", "UC"}:
            raise ValueError("invalid status")

        updated = crud.update_item(item_id, BacklogItemUpdate(**update_data))
        return {
            "ok": True,
            "item_id": updated.id,
            "updated_fields": update_data,
        }
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}

async def find_item_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search items by fuzzy match in title."""
    try:
        data = _FindArgs(**args)
        items = crud.get_items(data.project_id, type=data.type)
        q = data.query.lower()
        matches = [
            {"id": it.id, "title": it.title, "type": it.type}
            for it in items
            if q in it.title.lower()
        ]
        return {"ok": True, "matches": matches}
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}


async def get_item_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch a single item by id or by lookup."""
    try:
        data = _GetArgs(**args)
        if data.id is not None:
            item = crud.get_item(data.id)
            if not item:
                return {"ok": False, "error": "item_not_found"}
        else:
            items = crud.get_items(data.project_id, type=data.type)
            matches = [
                it
                for it in items
                if it.title.lower() == data.title.lower()
            ]
            if not matches:
                return {"ok": False, "error": "item_not_found"}
            if len(matches) > 1:
                return {"ok": False, "error": "item_ambiguous"}
            item = matches[0]
        return {
            "ok": True,
            "result": {
                "id": item.id,
                "type": item.type,
                "title": item.title,
                "description": getattr(item, "description", ""),
                "status": getattr(item, "status", None),
                "parent_id": item.parent_id,
            },
        }
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}


async def list_items_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """List items for a project with optional filters."""
    try:
        data = _ListArgs(**args)
        items = crud.get_items(
            data.project_id, type=data.type, limit=data.limit, offset=data.offset
        )
        if data.query:
            q = data.query.lower()
            items = [it for it in items if q in it.title.lower()]
        result = [
            {
                "id": it.id,
                "type": it.type,
                "title": it.title,
                "parent_id": it.parent_id,
                "status": getattr(it, "status", None),
            }
            for it in items
        ]
        return {"ok": True, "result": result}
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}


async def delete_item_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete an item and its descendants."""
    try:
        data = _DeleteArgs(**args)
        item = crud.get_item(data.id)
        if not item:
            return {"ok": False, "error": "item_not_found"}
        deleted = crud.delete_item(data.id)
        return {"ok": True, "result": {"deleted": deleted}}
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}


async def move_item_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Reparent an item while enforcing hierarchy rules."""
    try:
        data = _MoveArgs(**args)
        item = crud.get_item(data.id)
        if not item:
            return {"ok": False, "error": "item_not_found"}
        new_parent = crud.get_item(data.new_parent_id)
        if not new_parent or new_parent.project_id != item.project_id:
            return {"ok": False, "error": "invalid_parent"}
        if new_parent.id == item.id:
            return {"ok": False, "error": "cycle_detected"}
        if item.parent_id == new_parent.id:
            return {
                "ok": True,
                "result": {
                    "id": item.id,
                    "type": item.type,
                    "title": item.title,
                    "parent_id": item.parent_id,
                    "status": getattr(item, "status", None),
                },
            }
        allowed = _ALLOWED_PARENT.get(item.type, [])
        if new_parent.type not in allowed:
            return {"ok": False, "error": "invalid_parent_type"}
        current = new_parent
        while current.parent_id is not None:
            if current.parent_id == item.id:
                return {"ok": False, "error": "cycle_detected"}
            current = crud.get_item(current.parent_id)
            if current is None:
                break
        updated = crud.update_item(item.id, BacklogItemUpdate(parent_id=new_parent.id))
        return {
            "ok": True,
            "result": {
                "id": updated.id,
                "type": updated.type,
                "title": updated.title,
                "parent_id": updated.parent_id,
                "status": getattr(updated, "status", None),
            },
        }
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}


async def summarize_project_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Summarise project structure and counts."""
    try:
        data = _SummarizeArgs(**args)
        items = crud.get_items(data.project_id, limit=1000)
        counts = Counter(it.type for it in items)
        children = defaultdict(list)
        for it in items:
            children[it.parent_id].append(it)

        def walk(parent_id: int | None, depth: int, level: int = 0) -> List[str]:
            lines: List[str] = []
            if depth <= 0:
                return lines
            for child in children.get(parent_id, []):
                lines.append("  " * level + f"{child.type}: {child.title}")
                lines.extend(walk(child.id, depth - 1, level + 1))
            return lines

        text = "\n".join(walk(None, data.depth)) or "(empty)"
        result = {
            "text": text,
            "counts": {t: counts.get(t, 0) for t in ["Epic", "Capability", "Feature", "US", "UC"]},
        }
        return {"ok": True, "result": result}
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}


async def bulk_create_features_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create multiple features under a parent item."""
    try:
        data = _BulkCreateArgs(**args)
        parent = crud.get_item(data.parent_id)
        if not parent or parent.project_id != data.project_id:
            return {"ok": False, "error": "invalid_parent"}
        if parent.type not in {"Epic", "Capability"}:
            return {"ok": False, "error": "invalid_parent_type"}
        existing = {
            it.title.lower()
            for it in crud.get_items(data.project_id, type="Feature", limit=1000)
            if it.parent_id == data.parent_id
        }
        created_ids: List[int] = []
        seen: set[str] = set()
        for item in data.items:
            title_key = item.title.lower()
            if title_key in existing or title_key in seen:
                continue
            feature = FeatureCreate(
                title=item.title,
                description=item.description or "",
                project_id=data.project_id,
                parent_id=data.parent_id,
            )
            created = crud.create_item(feature)
            created_ids.append(created.id)
            seen.add(title_key)
        return {"ok": True, "result": {"created_ids": created_ids}}
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Document handlers
# ---------------------------------------------------------------------------

async def list_documents_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    project_id = int(args["project_id"])
    docs = [d.model_dump() for d in crud.get_documents(project_id)]
    return {"ok": True, "documents": docs}


async def search_documents_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    project_id = int(args["project_id"]); query = str(args["query"])
    chunks = crud.get_all_document_chunks_for_project(project_id)
    if not chunks: return {"ok": True, "matches": []}
    q = await embed_text(query)
    scored = []
    for c in chunks:
        emb = c.get("embedding")
        if not emb: continue
        score = cosine_similarity(emb, q)
        if score <= 0: continue
        text = c.get("text", "")
        # make a short snippet
        snippet = text[:360] + ("…" if len(text) > 360 else "")
        scored.append({"doc_id": c["doc_id"], "chunk_index": c["chunk_index"], "score": float(score), "snippet": snippet})
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:8]
    return {"ok": True, "matches": top}


async def get_document_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    doc_id = int(args["doc_id"])
    doc = crud.get_document(doc_id)
    if not doc:
        return {"ok": False, "error": "Document not found"}
    return {
        "ok": True,
        "content": doc.get("content", ""),
        "filename": doc.get("filename"),
    }

# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _resolve_parent_hint(project_id: int, hint: Optional[str]) -> Optional[int]:
    """Best-effort mapping from hint like 'Epic: Foo' to an existing item id."""
    if not hint or ":" not in hint:
        return None
    type_part, title_part = [p.strip() for p in hint.split(":", 1)]
    items = crud.get_items(project_id, type=type_part)
    for it in items:
        if it.title.lower().startswith(title_part.lower()):
            return it.id
    return None


# JSON schema describing the features extracted by the LLM
FEATURES_SCHEMA = {
    "type": "object",
    "properties": {
        "features": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "maxLength": 120},
                    "objective": {"type": "string"},
                    "business_value": {"type": "string"},
                    "acceptance_criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": 4,
                    },
                    "parent_hint": {"type": ["string", "null"]},
                },
                "required": [
                    "title",
                    "objective",
                    "business_value",
                    "acceptance_criteria",
                ],
            },
            "minItems": 5,
            "maxItems": 10,
        }
    },
    "required": ["features"],
    "additionalProperties": False,
}


def _build_llm_json_schema() -> ChatOpenAI:
    """Construct ChatOpenAI instance enforcing FEATURES_SCHEMA."""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        return ChatOpenAI(
            model=model,
            temperature=0.2,
            timeout=30,
            model_kwargs={
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "features_extraction_schema",
                        "schema": FEATURES_SCHEMA,
                        "strict": True,
                    },
                }
            },
        )
    except TypeError:
        # Older versions may not support response_format
        return ChatOpenAI(model=model, temperature=0.2, timeout=30)


async def _call_llm(excerpts: str) -> List[GeneratedFeature]:
    """Call LLM with prompt and return parsed features list."""
    llm = _build_llm_json_schema()

    prompt = FEATURES_FROM_EXCERPTS_PROMPT.replace("{{excerpts}}", excerpts)
    response = llm.invoke([{ "role": "user", "content": prompt }])
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.endswith("```"):
        content = content[:-3]
    logger.info("LLM raw JSON length=%d", len(content))
    logger.debug("LLM raw JSON preview: %s", content[:500])
    try:
        return GeneratedFeatures.model_validate_json(content).features
    except ValidationError as e:
        logger.error("JSON validation failed: %s", e)
        return []


def _get_document_text(doc_id: int) -> str:
    doc = crud.get_document(doc_id)
    return doc.get("content", "") if doc else ""


# ---------------------------------------------------------------------------
# Draft features handler
# ---------------------------------------------------------------------------

async def draft_features_from_matches_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Draft and create Features from document matches."""
    try:
        project_id = int(args["project_id"])
        doc_query = str(args["doc_query"])
        k = int(args.get("k", 6))

        # Retrieve relevant chunks with higher recall
        chunks = crud.get_all_document_chunks_for_project(project_id)
        if not chunks:
            return {"ok": True, "items": []}
        q_emb = await embed_text(doc_query)
        scored: List[Dict[str, Any]] = []
        for c in chunks:
            emb = c.get("embedding")
            if not emb:
                continue
            score = cosine_similarity(emb, q_emb)
            if score < 0.45:
                continue
            scored.append({"doc_id": c["doc_id"], "text": c.get("text", ""), "score": float(score)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        top = scored[:20]
        excerpts = []
        total = 0
        for s in top:
            t = s["text"]
            if total + len(t) > 4000:
                t = t[: max(0, 4000 - total)]
            excerpts.append(t)
            total += len(t)
            if total >= 4000:
                break
        excerpt_text = "\n---\n".join(excerpts)
        logger.info(
            "draft_features_from_matches: matches=%d top_score=%.2f excerpt_len=%d",
            len(top),
            top[0]["score"] if top else 0.0,
            len(excerpt_text),
        )
        features = await _call_llm(excerpt_text)

        # Fallback to full document text if no features
        if not features and top:
            doc_text = _get_document_text(top[0]["doc_id"])[:12000]
            logger.info("Fallback to full document text of length %d", len(doc_text))
            features = await _call_llm(doc_text)

        if not features:
            return {"ok": True, "items": []}

        created_items = []
        for feat in features[:k]:
            parent_id = _resolve_parent_hint(project_id, feat.parent_hint)
            description = (
                f"{feat.objective}\n\nValeur métier:\n{feat.business_value}\n\nCritères d'acceptation:\n- "
                + "\n- ".join(feat.acceptance_criteria)
            )
            item = FeatureCreate(
                project_id=project_id,
                parent_id=parent_id,
                title=feat.title,
                description=description,
                acceptance_criteria="\n".join(f"- {c}" for c in feat.acceptance_criteria),
            )
            created = crud.create_item(item)
            logger.info(
                "Created Feature id=%s title=%s parent=%s",
                created.id,
                created.title,
                parent_id,
            )
            created_items.append({"id": created.id, "title": created.title})

        return {"ok": True, "items": created_items}

    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}
