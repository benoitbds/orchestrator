import pytest
from orchestrator.embedding_service import EmbeddingService


@pytest.mark.asyncio
async def test_vector_search_top_result():
    service = EmbeddingService(api_key="test-key")
    query = [1.0, 0.0]
    chunks = [
        {"text": "match", "embedding": [0.9, 0.1]},
        {"text": "other", "embedding": [0.0, 1.0]},
    ]
    result = await service.find_similar_chunks(query, chunks, top_k=1)
    assert len(result) == 1
    assert result[0]["text"] == "match"


@pytest.mark.asyncio
async def test_vector_search_no_results():
    service = EmbeddingService(api_key="test-key")
    query = [1.0, 0.0]
    chunks = [
        {"text": "unrelated", "embedding": [0.0, 1.0]},
    ]
    result = await service.find_similar_chunks(query, chunks, top_k=5, similarity_threshold=0.9)
    assert result == []
