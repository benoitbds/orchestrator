import importlib
import pytest

from agents import embeddings as emb


class DummyEnc:
    def encode(self, text):
        return [0] * len(text.split())
    def decode(self, toks):
        return " ".join("x" for _ in toks)


def test_chunk_text_empty(monkeypatch):
    monkeypatch.setattr(emb.tiktoken, "get_encoding", lambda name: DummyEnc())
    assert emb.chunk_text("", target_tokens=10) == []


def test_chunk_text_long(monkeypatch):
    monkeypatch.setattr(emb.tiktoken, "get_encoding", lambda name: DummyEnc())
    text = "word " * 500
    chunks = emb.chunk_text(text, target_tokens=50, overlap_tokens=10)
    assert len(chunks) > 1


@pytest.mark.asyncio
async def test_embed_texts_missing_key(monkeypatch):
    monkeypatch.setattr(emb, "OPENAI_API_KEY", "")
    res = await emb.embed_texts(["a", "b"])
    assert res == [[], []]


def test_cosine_similarity():
    assert emb.cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert emb.cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0, abs=1e-6)
    assert emb.cosine_similarity([0, 0], [1, 2]) == 0.0
