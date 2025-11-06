"""Async handlers for backlog management tools."""
from __future__ import annotations

import os
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Literal, Union
import logging
import asyncio, json, re

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    field_validator,
    model_validator,
    constr,
)

from orchestrator import crud, stream
from orchestrator.prompt_loader import load_prompt
from agents.tools_context import get_current_run_id
# Load environment variables
load_dotenv()
try:  # pragma: no cover - fallback if embeddings not ready
    from .embeddings import embed_text, embed_texts, chunk_text, cosine_similarity
except Exception:  # pragma: no cover
    def embed_text(text: str) -> list[float]:
        return [0.0]

    async def embed_texts(texts: List[str]) -> List[List[float]]:
        return [[0.0] for _ in texts]

    def chunk_text(text: str, target_tokens: int = 400, overlap_tokens: int = 60) -> List[str]:
        return [text.strip()] if text else []

    def cosine_similarity(a: List[float], b: List[float]) -> float:
        return 0.0
from orchestrator.models import (
    BacklogItem,
    EpicCreate,
    CapabilityCreate,
    FeatureCreate,
    USCreate,
    UCCreate,
    BacklogItemUpdate,
)
from .schemas import FeatureInput, ensure_acceptance_list

# Logger
logger = logging.getLogger(__name__)

# Prompt templates
FEATURES_FROM_EXCERPTS_PROMPT = load_prompt("features_from_excerpts")


def _mark_ai_item(item_id: int) -> Optional[BacklogItem]:
    run_id = get_current_run_id()
    if not run_id:
        return None
    return crud.mark_item_ai_touch(item_id, run_id)


async def _reindex_document_if_needed(doc) -> bool:
    """Ensure a document has chunk embeddings; rebuild if missing."""
    total, with_embeddings = crud.document_chunk_stats(doc.id)
    if total > 0 and with_embeddings > 0:
        return False

    content = (doc.content or "").strip()
    if not content:
        return False

    crud.update_document_status(doc.id, "ANALYZING", None)

    chunks = chunk_text(content, target_tokens=400, overlap_tokens=60)
    if not chunks:
        crud.update_document_status(doc.id, "ERROR", {"error": "No analyzable content"})
        return False

    embeddings = await embed_texts(chunks)
    if len(embeddings) < len(chunks):
        embeddings.extend([[] for _ in range(len(chunks) - len(embeddings))])

    if not any(embeddings):
        crud.delete_document_chunks(doc.id)
        crud.update_document_status(doc.id, "ERROR", {"error": "Embedding generation failed"})
        return False

    payload = [(idx, chunk, embeddings[idx]) for idx, chunk in enumerate(chunks)]
    crud.delete_document_chunks(doc.id)
    if payload:
        crud.upsert_document_chunks(doc.id, payload)

    total, with_embeddings = crud.document_chunk_stats(doc.id)
    status = "ANALYZED" if with_embeddings else "ERROR"
    crud.update_document_status(doc.id, status, {"chunk_count": total})
    logger.info(
        "Indexed %s chunks, %s with embeddings (doc_id=%s)",
        total,
        with_embeddings,
        doc.id,
    )
    return with_embeddings > 0


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
    project_id: int
    type: Literal["Epic", "Capability", "Feature", "US", "UC"]
    reason: str
    explicit_confirm: bool = False


class _MoveArgs(BaseModel):
    id: int
    new_parent_id: int


class _SummarizeArgs(BaseModel):
    project_id: int
    depth: int = 3


class _BulkFeature(BaseModel):
    title: str
    description: str | None = None
    acceptance_criteria: Union[str, List[str]] | None = None

    @model_validator(mode="after")
    def _normalize_acceptance_criteria(self):
        ac = self.acceptance_criteria
        if ac is None:
            self.acceptance_criteria = ""
        elif isinstance(ac, list):
            cleaned = [str(x).strip() for x in ac if str(x).strip()]
            self.acceptance_criteria = "- " + "\n- ".join(cleaned) if cleaned else ""
        else:
            self.acceptance_criteria = str(ac).strip()
        return self


class _BulkCreateArgs(BaseModel):
    project_id: int
    parent_id: int
    items: List[FeatureInput]

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
        marked = _mark_ai_item(created.id)
        if marked:
            created = marked
        return {
            "ok": True,
            "item_id": created.id,
            "type": created.type,
            "title": created.title,
        }
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# generate_items_from_parent handler
# ---------------------------------------------------------------------------

MAX_PARENT = 1500
MAX_CTX = 600
MAX_DOCS = 1200
ALLOWED_TYPES = {"Feature", "US", "UC"}


class _GenerateArgs(BaseModel):
    project_id: int
    parent_id: int
    target_type: str
    n: int | None = 6
    format: str | None = None
    dedup: bool | None = None
    trace_to_doc: bool | None = None


def _build_llm_json_object():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        timeout=30,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def _short(text: str, limit: int) -> str:
    t = (text or "").strip()
    return t if len(t) <= limit else t[:limit].rsplit(" ", 1)[0] + "…"


async def _project_summary(project_id: int) -> str:
    try:
        res = await summarize_project_tool({"project_id": project_id, "depth": 2})
        if res.get("ok"):
            return res["result"].get("text", "")
    except Exception:
        pass
    return ""


async def _doc_context_if_needed(project_id: int, title: str, desc: str) -> str:
    if len(desc or "") >= 400:
        return ""
    try:
        res = await search_documents_handler({"project_id": project_id, "query": title})
        blobs = [m.get("snippet", "") for m in res.get("matches", [])]
        return _short(" ".join(blobs), MAX_DOCS)
    except Exception:
        return ""


async def _list_related_items(project_id: int, parent: Any) -> List[Dict[str, Any]]:
    items = crud.get_items(project_id, limit=200)
    out: List[Dict[str, Any]] = []
    for it in items:
        if it.id == parent.id:
            continue
        if it.type in {"Epic", "Feature", "US", "UC", "Capability"}:
            out.append({"id": it.id, "type": it.type, "title": it.title or ""})
        if len(out) >= 12:
            break
    return out


def _validate_feature(d: Dict[str, Any]) -> Dict[str, Any] | None:
    req = {"title", "objective", "business_value", "acceptance_criteria"}
    if not isinstance(d, dict) or not req.issubset(d.keys()):
        return None
    ac = d.get("acceptance_criteria") or []
    if not isinstance(ac, list) or len(ac) < 2:
        return None
    return {
        "title": str(d["title"])[:120].strip(),
        "objective": str(d["objective"]).strip(),
        "business_value": str(d["business_value"]).strip(),
        "acceptance_criteria": [str(x).strip() for x in ac if str(x).strip()],
        "assumptions": [str(x).strip() for x in (d.get("assumptions") or []) if str(x).strip()],
    }


def _validate_us(d: Dict[str, Any]) -> Dict[str, Any] | None:
    req = {"title", "as_a", "i_want", "so_that", "acceptance_criteria"}
    if not isinstance(d, dict) or not req.issubset(d.keys()):
        return None
    ac = d.get("acceptance_criteria") or []
    if not isinstance(ac, list) or len(ac) < 2:
        return None
    pr = d.get("priority", "Should")
    if pr not in {"Must", "Should", "Could"}:
        pr = "Should"
    try:
        est = int(d.get("estimate", 3))
    except Exception:
        est = 3
    return {
        "title": str(d["title"])[:120].strip(),
        "as_a": str(d["as_a"]).strip(),
        "i_want": str(d["i_want"]).strip(),
        "so_that": str(d["so_that"]).strip(),
        "acceptance_criteria": [str(x).strip() for x in ac if str(x).strip()],
        "priority": pr,
        "estimate": est,
        "dependencies": [str(x).strip() for x in (d.get("dependencies") or []) if str(x).strip()],
    }


def _validate_uc(d: Dict[str, Any]) -> Dict[str, Any] | None:
    req = {"title", "actors", "preconditions", "main_flow", "postconditions"}
    if not isinstance(d, dict) or not req.issubset(d.keys()):
        return None

    def _lst(k: str) -> List[str]:
        v = d.get(k) or []
        return [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else []

    alt = d.get("alternate_flows") or []
    if isinstance(alt, list):
        alt = [[str(x).strip() for x in flow if str(x).strip()] for flow in alt if isinstance(flow, list)]
    else:
        alt = []
    return {
        "title": str(d["title"])[:120].strip(),
        "actors": _lst("actors"),
        "preconditions": _lst("preconditions"),
        "main_flow": _lst("main_flow"),
        "alternate_flows": alt,
        "postconditions": _lst("postconditions"),
        "non_functional_notes": _lst("non_functional_notes"),
    }


def _validate_payload(target_type: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = data.get("items", [])
    out: List[Dict[str, Any]] = []
    for it in items:
        v = None
        if target_type == "Feature":
            v = _validate_feature(it)
        elif target_type == "US":
            v = _validate_us(it)
        elif target_type == "UC":
            v = _validate_uc(it)
        if v:
            out.append(v)
    return out[:10]


def _similar(a: str, b: str) -> float:
    set_a = set(re.findall(r"\w+", a.lower()))
    set_b = set(re.findall(r"\w+", b.lower()))
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    return inter / max(len(set_a), len(set_b))


async def _dedup_titles(candidates: List[Dict[str, Any]], existing: List[Dict[str, Any]], threshold: float = 0.85):
    ex_titles = [e["title"] for e in existing if e.get("title")]
    out = []
    for c in candidates:
        t = c.get("title", "")
        if t and max((_similar(t, et) for et in ex_titles), default=0.0) >= threshold:
            continue
        out.append(c)
    return out


def _describe_feature(v: Dict[str, Any]) -> str:
    parts = [
        v["objective"],
        f"\n\nValeur métier:\n{v['business_value']}",
        "\n\nCritères d'acceptation:\n- " + "\n- ".join(v["acceptance_criteria"]),
    ]
    if v.get("assumptions"):
        parts.append("\n\nHypothèses:\n- " + "\n- ".join(v["assumptions"]))
    return "".join(parts)


def _describe_us(v: Dict[str, Any]) -> str:
    return (
        f"**En tant que** {v['as_a']}\n"
        f"**Je veux** {v['i_want']}\n"
        f"**Afin de** {v['so_that']}\n\n"
        f"**Critères d'acceptation**:\n- " + "\n- ".join(v["acceptance_criteria"]) + "\n\n"
        f"**Priorité**: {v['priority']}  |  **Estimation**: {v['estimate']} pts"
    )


def _describe_uc(v: Dict[str, Any]) -> str:
    parts = []
    if v["actors"]:
        parts.append("**Acteurs**:\n- " + "\n- ".join(v["actors"]))
    if v["preconditions"]:
        parts.append("**Préconditions**:\n- " + "\n- ".join(v["preconditions"]))
    if v["main_flow"]:
        parts.append("**Flux nominal**:\n" + "\n".join(v["main_flow"]))
    for idx, flow in enumerate(v.get("alternate_flows", []), start=1):
        parts.append(f"**Flux alternatif A{idx}**:\n" + "\n".join(flow))
    if v["postconditions"]:
        parts.append("**Postconditions**:\n- " + "\n- ".join(v["postconditions"]))
    if v.get("non_functional_notes"):
        parts.append(
            "**Notes non-fonctionnelles**:\n- " + "\n- ".join(v["non_functional_notes"])
        )
    return "\n\n".join(parts)


async def _call_llm_with_backoff(llm, prompt: str) -> str:
    for attempt, wait in enumerate((0.8, 2.0, 5.0), start=1):
        try:
            resp = await asyncio.to_thread(llm.invoke, [HumanMessage(content=prompt)])
            return getattr(resp, "content", None) or resp.generations[0].message.content
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < 3:
                await asyncio.sleep(wait)
                continue
            raise


def _parse_json(raw: str | None) -> Dict[str, Any]:
    if not raw:
        return {"items": []}
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, flags=re.S)
        return json.loads(m.group(0)) if m else {"items": []}


async def _create_items(validated: List[Dict[str, Any]], project_id: int, parent_id: int, target_type: str) -> List[Dict[str, Any]]:
    created = []
    for v in validated:
        if target_type == "Feature":
            desc = _describe_feature(v)
            item = FeatureCreate(
                project_id=project_id,
                parent_id=parent_id,
                title=v["title"],
                description=desc,
                acceptance_criteria="\n".join(v["acceptance_criteria"]),
            )
        elif target_type == "US":
            desc = _describe_us(v)
            item = USCreate(
                project_id=project_id,
                parent_id=parent_id,
                title=v["title"],
                description=desc,
                acceptance_criteria="\n".join(v["acceptance_criteria"]),
                story_points=v["estimate"],
            )
        else:
            desc = _describe_uc(v)
            item = UCCreate(
                project_id=project_id,
                parent_id=parent_id,
                title=v["title"],
                description=desc,
            )
        created_item = crud.create_item(item)
        marked = _mark_ai_item(created_item.id)
        if marked:
            created_item = marked
        created.append({"id": created_item.id, "title": created_item.title})
    return created


def build_prompt_universal(target_type: str, n: int, parent: Dict[str, Any], project_ctx: str, items_existants: List[Dict[str, Any]], doc_ctx: str) -> str:
    return f"""
Tu es Product Manager senior et Business Analyst.
Objectif: produire {n} éléments de type {target_type} sous l'item parent ci-dessous.
Qualité:
- Déduplication avec items_existants (éviter titres quasi-identiques).
- Traçabilité: si pertinent, ajouter 'sources' (doc:#|titre|page).
- Sortie STRICTEMENT JSON valide selon le schéma ci-dessous. Aucune prose hors JSON.

Entrées:
- target_type: {target_type}
- n: {n}
- item_parent: {{
  "id": {parent['id']},
  "type": "{parent.get('type','')}",
  "title": "{parent.get('title','').replace('"','\\"')}",
  "description": "{_short(parent.get('description',''), MAX_PARENT).replace('"','\\"')}"
}}
- contexte_projet (<=600): "{_short(project_ctx, MAX_CTX).replace('"','\\"')}"
- items_existants (<=12): {json.dumps(items_existants, ensure_ascii=False)}
- extraits_documents (<=1200): "{doc_ctx.replace('"','\\"') if doc_ctx else ''}"

Consignes par type:
- Feature: champs title, objective, business_value, acceptance_criteria[2..4], assumptions(optional).
- US: title, as_a, i_want, so_that, acceptance_criteria[2..5] (Gherkin Given/When/Then), priority(Must|Should|Could), estimate(1|2|3|5|8), dependencies(optional).
- UC: title, actors[], preconditions[], main_flow[], alternate_flows[[]], postconditions[], non_functional_notes(optional).

Schéma de sortie JSON:
{{
  "parent_id": {parent['id']},
  "type": "{target_type}",
  "items": [ ... ]
}}
Réponds uniquement avec le JSON.
""".strip()


async def generate_items_from_parent_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data = _GenerateArgs(**args)
    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}

    project_id = data.project_id
    parent_id = data.parent_id
    target_type = data.target_type.upper() if data.target_type.lower() in {"us", "uc"} else data.target_type.capitalize()
    n = max(1, min(10, data.n or 6))
    if target_type not in ALLOWED_TYPES:
        return {"ok": False, "error": f"Unsupported target_type: {target_type}"}

    parent = crud.get_item(parent_id)
    if not parent or parent.project_id != project_id:
        return {"ok": False, "error": "parent_not_found"}

    parent_dict = {
        "id": parent.id,
        "type": parent.type,
        "title": parent.title or "",
        "description": parent.description or "",
    }

    proj_summary = await _project_summary(project_id)
    items_existants = await _list_related_items(project_id, parent)
    doc_ctx = await _doc_context_if_needed(project_id, parent.title or "", parent.description or "")
    prompt = build_prompt_universal(target_type, n, parent_dict, proj_summary or "", items_existants, doc_ctx or "")

    llm = _build_llm_json_object()
    raw = await _call_llm_with_backoff(llm, prompt)
    data_json = _parse_json(raw)
    validated = _validate_payload(target_type, data_json)
    if not validated:
        return {"ok": True, "items": []}
    validated = await _dedup_titles(validated, items_existants)
    created = await _create_items(validated, project_id, parent_id, target_type)
    logger.info(
        "generate_items_from_parent: created=%d target_type=%s parent_id=%s",
        len(created),
        target_type,
        parent_id,
    )
    return {"ok": True, "items": created}

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
        marked = _mark_ai_item(item_id)
        if marked:
            updated = marked
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
        logger.info(
            "%s",
            {
                "tool": "delete_item",
                "why": data.reason,
                "confirmed": data.explicit_confirm,
            },
        )
        if not data.reason or data.reason.strip().lower() == "cleanup":
            return {"ok": False, "error": "invalid_reason"}
        if not data.explicit_confirm:
            return {"ok": False, "error": "explicit_confirm_required"}
        item = crud.get_item(data.id)
        if not item:
            return {"ok": False, "error": "item_not_found"}
        deleted = crud.delete_item(data.id)
        return {"ok": True, "item_id": data.id, "result": {"deleted": deleted}}
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
        marked = _mark_ai_item(item.id)
        if marked:
            updated = marked
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
        if not parent:
            return {"ok": False, "error": "invalid_parent"}
        if parent.project_id != data.project_id:
            return {
                "ok": False,
                "error": "PARENT_PROJECT_MISMATCH",
                "status": 409,
                "message": "parent_id belongs to another project",
            }
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
                acceptance_criteria=(item.acceptance_criteria or ""),
            )
            created = crud.create_item(feature)
            _mark_ai_item(created.id)
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




@tool("return_features", return_direct=True)
def return_features(features: List[Dict]):
    """Return extracted product features (schema-enforced by the tool signature)."""
    return {"features": features}


TOOLS = [return_features]


def _build_llm_tools() -> ChatOpenAI:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model, temperature=0.2, timeout=30)


def _tool_schema_instruction() -> str:
    return (
        "You MUST call the `return_features` tool ONCE with a single argument: "
        "{'features': [ { 'title': str, 'objective': str, 'business_value': str, "
        "'acceptance_criteria': [str, ...], 'parent_hint': str|null } ... ] } . "
        "Create 5-10 features. Stay in French."
    )


def _validate_features_payload(payload: Dict[str, Any]) -> List[GeneratedFeature]:
    try:
        return GeneratedFeatures.model_validate(payload).features
    except ValidationError as e:
        logger.error("Tool payload validation failed: %s", e)
        return []


async def _call_llm(excerpts_text: str) -> List[GeneratedFeature]:
    """Call LLM using tool calling and return validated features."""
    llm = _build_llm_tools()
    user = HumanMessage(content=_tool_schema_instruction() + "\n\nEXTRACTS:\n" + excerpts_text)
    resp = llm.bind_tools(TOOLS).invoke([user])
    tool_calls = getattr(resp, "tool_calls", []) or []
    for call in tool_calls:
        if call.get("name") == "return_features":
            args = call.get("args") if isinstance(call.get("args"), dict) else {}
            feats = args.get("features", [])
            return _validate_features_payload({"features": feats})
    return []


def _get_document_text(doc_id: int) -> str:
    doc = crud.get_document(doc_id)
    return doc.get("content", "") if doc else ""



_SECTION_ALIASES: Dict[str, str] = {
    "exigences fonctionnelles": "Exigences fonctionnelles",
    "exigence fonctionnelle": "Exigences fonctionnelles",
    "nfr": "NFR",
    "non functional requirements": "NFR",
    "gouvernance": "Gouvernance",
    "objectifs kpi": "Objectifs & KPI",
    "objectifs & kpi": "Objectifs & KPI",
    "objectifs et kpi": "Objectifs & KPI",
}
_BULLET_CHAR = "\u2022"



def _match_fallback_section(line: str) -> Optional[str]:
    normalized = re.sub(r"[^a-z0-9& ]+", " ", line.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return None
    for key, label in _SECTION_ALIASES.items():
        if key in normalized:
            return label
    return None


def _is_heading_like(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s.startswith("#") or s.startswith("=="):
        return True
    if re.match(r"^\d+[\.)]\s", s):
        return True
    if s.endswith(":") and len(s) <= 80:
        return True
    if len(s) <= 60 and s == s.upper() and any(ch.isalpha() for ch in s):
        return True
    return False


def _clean_bullet(line: str) -> str:
    stripped = line.lstrip()
    if not stripped:
        return ""
    if stripped[0] in {"-", "*", _BULLET_CHAR}:
        stripped = stripped[1:]
    stripped = stripped.lstrip("-" + _BULLET_CHAR + "*[] ")
    return stripped.strip()


def _is_bullet_line(line: str) -> bool:
    return line.lstrip().startswith(("-", "*", _BULLET_CHAR))


def _bullet_acceptance_criteria(bullet: str) -> List[str]:
    parts = [p.strip() for p in re.split(r"[.;](?:\s+|$)", bullet) if p.strip()]
    unique: List[str] = []
    for part in parts:
        if part not in unique:
            unique.append(part)
        if len(unique) >= 3:
            break
    if len(unique) >= 2:
        return [f"{p}." if not p.endswith(".") else p for p in unique[:3]]
    if unique:
        base = unique[0]
        filler = f'Compléter les détails sur "{base}".'
        return [f"{base}." if not base.endswith(".") else base, filler]
    cleaned = bullet.strip()
    if cleaned:
        return [f"{cleaned}." if not cleaned.endswith(".") else cleaned, "Valider avec les parties prenantes."]
    return ["Clarifier le besoin.", "Valider avec les parties prenantes."]


def _fallback_parse_documents(fallback_doc_ids: List[int], limit: int) -> List[GeneratedFeature]:
    features: List[GeneratedFeature] = []
    seen_titles: set[str] = set()
    for doc_id in fallback_doc_ids:
        content = _get_document_text(doc_id)
        if not content:
            continue
        current_section: Optional[str] = None
        for raw_line in content.splitlines():
            if not raw_line.strip():
                continue
            maybe_section = _match_fallback_section(raw_line)
            if maybe_section:
                current_section = maybe_section
                continue
            if _is_heading_like(raw_line) and not _is_bullet_line(raw_line):
                current_section = None
                continue
            if not current_section or not _is_bullet_line(raw_line):
                continue
            bullet = _clean_bullet(raw_line)
            if not bullet:
                continue
            title = bullet.strip()
            if len(title) > 120:
                title = title[:117].rstrip() + "..."
            if not title or title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            acceptance = _bullet_acceptance_criteria(bullet)
            bullet_text = bullet.strip()
            objective = f"Formaliser: {bullet_text}"
            if not objective.endswith("."):
                objective += "."
            feature = GeneratedFeature(
                title=title,
                objective=objective,
                business_value=f"Répond aux besoins documentés dans la section {current_section}.",
                acceptance_criteria=acceptance,
                parent_hint=None,
            )
            features.append(feature)
            if len(features) >= limit:
                return features
    return features


# ---------------------------------------------------------------------------
# Draft features handler
# ---------------------------------------------------------------------------


async def draft_features_from_matches_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Draft and create Features from document matches."""
    try:
        project_id = int(args["project_id"])
        doc_query = str(args["doc_query"])
        k = int(args.get("k", 6))
        fallback_parse_full_doc = bool(args.get("fallback_parse_full_doc", False))

        documents = crud.get_documents(project_id)
        reindexed_any = False
        for doc in documents:
            status = getattr(doc, "status", "UPLOADED")
            if status == "ANALYZED" and await _reindex_document_if_needed(doc):
                reindexed_any = True

        if reindexed_any:
            documents = crud.get_documents(project_id)

        analyzed_doc_ids = {doc.id for doc in documents if getattr(doc, "status", "ANALYZED") == "ANALYZED"}
        if documents and not analyzed_doc_ids and not fallback_parse_full_doc:
            return {
                "ok": False,
                "error": "NO_MATCHES",
                "message": "Document not indexed or no relevant passages. Run Analyze then retry.",
            }

        # Retrieve relevant chunks with higher recall
        chunks = crud.get_all_document_chunks_for_project(project_id)
        if not chunks and not fallback_parse_full_doc:
            return {
                "ok": False,
                "error": "NO_MATCHES",
                "message": "Document not indexed or no relevant passages. Run Analyze then retry.",
            }
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
        excerpts: List[str] = []
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

        top_score = top[0]["score"] if top else 0.0
        if top and top_score < 0.2 and not fallback_parse_full_doc:
            return {
                "ok": False,
                "error": "NO_MATCHES",
                "message": "Document not indexed or no relevant passages. Run Analyze then retry.",
            }

        if not top:
            if not fallback_parse_full_doc:
                return {
                    "ok": False,
                    "error": "NO_MATCHES",
                    "message": "Document not indexed or no relevant passages. Run Analyze then retry.",
                }
        features = await _call_llm(excerpt_text)
        fallback_source: Optional[str] = None

        # Fallback to full document text if no features
        if not features and top:
            doc_text = _get_document_text(top[0]["doc_id"])[:12000]
            logger.info("Fallback to full document text of length %d", len(doc_text))
            if doc_text:
                features = await _call_llm(doc_text)

        fallback_doc_ids = list(dict.fromkeys(s["doc_id"] for s in top))
        if not fallback_doc_ids and documents:
            fallback_doc_ids = [doc.id for doc in documents]
        if not features and fallback_parse_full_doc and fallback_doc_ids:
            parsed = _fallback_parse_documents(fallback_doc_ids, k)
            if parsed:
                logger.info(
                    "Fallback parse extracted %d features from sections for doc_ids=%s",
                    len(parsed),
                    fallback_doc_ids,
                )
                features = parsed
                fallback_source = "fallback_parse"

        if not features:
            return {"ok": True, "items": []}

        created_items = []
        for feat in features[:k]:
            parent_id = _resolve_parent_hint(project_id, feat.parent_hint)
            ac_lines = ensure_acceptance_list(feat.acceptance_criteria)
            description = (
                f"{feat.objective}\n\nValeur métier:\n{feat.business_value}\n\nCritères d'acceptation:\n- "
                + "\n- ".join(ac_lines)
            )
            item = FeatureCreate(
                project_id=project_id,
                parent_id=parent_id,
                title=feat.title,
                description=description,
                acceptance_criteria="\n".join(f"- {c}" for c in ac_lines),
            )
            created = crud.create_item(item)
            _mark_ai_item(created.id)
            logger.info(
                "Created Feature id=%s title=%s parent=%s",
                created.id,
                created.title,
                parent_id,
            )
            created_items.append({"id": created.id, "title": created.title})
        response: Dict[str, Any] = {"ok": True, "items": created_items}
        if fallback_source:
            response["source"] = fallback_source

        return response

    except (ValidationError, ValueError) as e:
        return {"ok": False, "error": str(e)}
