from __future__ import annotations
from __future__ import annotations

"""Utilities for chunking text, embedding via OpenAI, and cosine similarity."""
import logging
import os
from typing import List

import httpx
import numpy as np
import tiktoken

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
logger = logging.getLogger(__name__)


def _tokenize_len(text: str, model: str = "text-embedding-3-small") -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text or ""))


def chunk_text(text: str, target_tokens: int = 400, overlap_tokens: int = 60) -> List[str]:
    """Split text into overlapping chunks based on token count."""
    if not text:
        return []
    enc = tiktoken.get_encoding("cl100k_base")
    toks = enc.encode(text)
    chunks: List[str] = []
    i = 0
    n = len(toks)
    while i < n:
        j = min(i + target_tokens, n)
        chunk = enc.decode(toks[i:j])
        chunks.append(chunk.strip())
        step = j - i
        i = j - overlap_tokens if step > overlap_tokens else j
    return [c for c in chunks if c]


async def embed_texts(texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    """Embed a list of texts using OpenAI's embeddings API.

    Returns empty lists when the API key is missing or requests fail.
    """
    if not texts:
        return []
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-test"):
        logger.warning("OPENAI_API_KEY missing; returning empty embeddings")
        return [[] for _ in texts]

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    out: List[List[float]] = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(texts), 96):
            batch = texts[i : i + 96]
            body = {"model": model, "input": batch}
            try:
                r = await client.post(
                    "https://api.openai.com/v1/embeddings", headers=headers, json=body
                )
                r.raise_for_status()
                data = r.json()
                out.extend([d["embedding"] for d in data.get("data", [])])
            except httpx.HTTPError as exc:  # pragma: no cover - network failure
                logger.warning("embedding request failed: %s", exc)
                out.extend([[] for _ in batch])
    return out


def cosine_similarity(a: List[float], b: List[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)


async def embed_text(text: str) -> List[float]:
    res = await embed_texts([text])
    return res[0] if res else []
