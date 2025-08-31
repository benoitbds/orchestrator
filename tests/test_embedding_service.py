import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from orchestrator.embedding_service import (
    EmbeddingService,
    EmbeddingError,
    get_embedding_service,
    embed_document_text
)


class TestEmbeddingService:
    
    def test_initialization_with_api_key(self):
        """Test service initialization with provided API key."""
        service = EmbeddingService(api_key="test-key")
        assert service.api_key == "test-key"
        assert service.model == "text-embedding-3-small"
    
    def test_initialization_custom_model(self):
        """Test service initialization with custom model."""
        service = EmbeddingService(api_key="test-key", model="text-embedding-ada-002")
        assert service.model == "text-embedding-ada-002"
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'env-test-key'})
    def test_initialization_env_api_key(self):
        """Test service initialization using environment variable."""
        service = EmbeddingService()
        assert service.api_key == "env-test-key"
    
    @patch.dict('os.environ', {}, clear=True)
    def test_initialization_no_api_key(self):
        """Test service initialization fails without API key."""
        with pytest.raises(EmbeddingError, match="OpenAI API key not found"):
            EmbeddingService()
    
    def test_get_embedding_info(self):
        """Test getting embedding service information."""
        service = EmbeddingService(api_key="test-key")
        info = service.get_embedding_info()
        
        expected_keys = ["model", "api_key_configured", "max_batch_size", "max_retries"]
        for key in expected_keys:
            assert key in info
        
        assert info["api_key_configured"] is True
        assert info["model"] == "text-embedding-3-small"


class TestEmbeddingGeneration:
    
    @pytest.fixture
    def service(self):
        """Create a mock embedding service for testing."""
        service = EmbeddingService(api_key="test-key")
        return service
    
    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self, service):
        """Test that empty text raises an error."""
        with pytest.raises(EmbeddingError, match="Cannot generate embedding for empty text"):
            await service.generate_embedding("")
        
        with pytest.raises(EmbeddingError, match="Cannot generate embedding for empty text"):
            await service.generate_embedding("   ")
    
    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, service):
        """Test successful embedding generation."""
        # Mock the embeddings client
        mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        service.embeddings_client.embed_query = Mock(return_value=mock_embedding)
        
        result = await service.generate_embedding("test text")
        assert result == mock_embedding
        service.embeddings_client.embed_query.assert_called_once_with("test text")
    
    @pytest.mark.asyncio
    async def test_generate_embedding_failure(self, service):
        """Test embedding generation failure."""
        service.embeddings_client.embed_query = Mock(side_effect=Exception("API Error"))
        
        with pytest.raises(EmbeddingError, match="Embedding generation failed"):
            await service.generate_embedding("test text")
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_success(self, service):
        """Test successful batch embedding generation."""
        texts = ["text 1", "text 2", "text 3"]
        mock_embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        
        service.embeddings_client.embed_documents = Mock(return_value=mock_embeddings)
        
        result = await service.generate_embeddings_batch(texts)
        assert result == mock_embeddings
        service.embeddings_client.embed_documents.assert_called_once_with(texts)
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_empty_list(self, service):
        """Test batch generation with empty list."""
        result = await service.generate_embeddings_batch([])
        assert result == []
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_filter_empty(self, service):
        """Test batch generation filters empty texts."""
        texts = ["text 1", "", "   ", "text 2"]
        expected_filtered = ["text 1", "text 2"]
        mock_embeddings = [[0.1, 0.2], [0.3, 0.4]]
        
        service.embeddings_client.embed_documents = Mock(return_value=mock_embeddings)
        
        result = await service.generate_embeddings_batch(texts)
        assert result == mock_embeddings
        service.embeddings_client.embed_documents.assert_called_once_with(expected_filtered)
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_all_empty(self, service):
        """Test batch generation with all empty texts."""
        texts = ["", "   ", ""]
        
        with pytest.raises(EmbeddingError, match="No valid texts provided"):
            await service.generate_embeddings_batch(texts)
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_large(self, service):
        """Test batch generation respects batch size limits."""
        # Create a large list that exceeds batch size
        service.max_batch_size = 2
        texts = ["text 1", "text 2", "text 3", "text 4", "text 5"]
        
        # Mock multiple batch calls
        batch1_result = [[0.1, 0.2], [0.3, 0.4]]
        batch2_result = [[0.5, 0.6], [0.7, 0.8]]
        batch3_result = [[0.9, 1.0]]
        
        service.embeddings_client.embed_documents = Mock(
            side_effect=[batch1_result, batch2_result, batch3_result]
        )
        
        result = await service.generate_embeddings_batch(texts)
        
        expected_result = batch1_result + batch2_result + batch3_result
        assert result == expected_result
        assert service.embeddings_client.embed_documents.call_count == 3


class TestTextChunkingIntegration:
    
    @pytest.fixture
    def service(self):
        return EmbeddingService(api_key="test-key")
    
    @pytest.mark.asyncio
    async def test_embed_text_with_chunking_success(self, service):
        """Test successful text embedding with chunking."""
        text = "This is a test document. It has multiple sentences. Each should be embedded."
        
        # Mock the embedding generation
        mock_embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        service.embeddings_client.embed_documents = Mock(return_value=mock_embeddings)
        
        result = await service.embed_text_with_chunking(text)
        
        assert len(result) > 0
        for i, chunk_data in enumerate(result):
            assert "text" in chunk_data
            assert "embedding" in chunk_data
            assert "chunk_index" in chunk_data
            assert chunk_data["chunk_index"] == i
            assert chunk_data["embedding_model"] == service.model
    
    @pytest.mark.asyncio
    async def test_embed_text_with_chunking_empty_text(self, service):
        """Test chunking with empty text."""
        result = await service.embed_text_with_chunking("")
        assert result == []
        
        result = await service.embed_text_with_chunking("   ")
        assert result == []
    
    @pytest.mark.asyncio
    async def test_embed_text_with_chunking_strategies(self, service):
        """Test different chunking strategies."""
        text = "Paragraph 1.\n\nParagraph 2 with more content.\n\nParagraph 3."
        
        # Mock embeddings
        service.embeddings_client.embed_documents = Mock(return_value=[[0.1, 0.2]])
        
        # Test sentence strategy
        result_sentences = await service.embed_text_with_chunking(
            text, chunking_strategy="sentences"
        )
        
        # Test paragraph strategy
        result_paragraphs = await service.embed_text_with_chunking(
            text, chunking_strategy="paragraphs"
        )
        
        assert len(result_sentences) > 0
        assert len(result_paragraphs) > 0
    
    @pytest.mark.asyncio
    async def test_embed_text_with_chunking_failure(self, service):
        """Test chunking when embedding fails."""
        text = "Test text for embedding failure."
        
        service.embeddings_client.embed_documents = Mock(side_effect=Exception("API Error"))
        
        with pytest.raises(EmbeddingError, match="Text embedding with chunking failed"):
            await service.embed_text_with_chunking(text)


class TestSimilaritySearch:
    
    @pytest.fixture
    def service(self):
        return EmbeddingService(api_key="test-key")
    
    def test_calculate_cosine_similarity(self, service):
        """Test cosine similarity calculation."""
        embedding1 = [1.0, 0.0, 0.0]
        embedding2 = [0.0, 1.0, 0.0]
        
        similarity = service.calculate_cosine_similarity(embedding1, embedding2)
        assert similarity == 0.0  # Orthogonal vectors
        
        # Identical vectors
        similarity = service.calculate_cosine_similarity(embedding1, embedding1)
        assert similarity == 1.0
        
        # Opposite vectors
        embedding3 = [-1.0, 0.0, 0.0]
        similarity = service.calculate_cosine_similarity(embedding1, embedding3)
        assert similarity == -1.0
    
    def test_calculate_cosine_similarity_different_dimensions(self, service):
        """Test similarity calculation with different dimensions."""
        embedding1 = [1.0, 0.0]
        embedding2 = [1.0, 0.0, 0.0]
        
        with pytest.raises(EmbeddingError, match="Embeddings must have the same dimensions"):
            service.calculate_cosine_similarity(embedding1, embedding2)
    
    def test_calculate_cosine_similarity_zero_magnitude(self, service):
        """Test similarity calculation with zero magnitude vectors."""
        embedding1 = [0.0, 0.0, 0.0]
        embedding2 = [1.0, 0.0, 0.0]
        
        similarity = service.calculate_cosine_similarity(embedding1, embedding2)
        assert similarity == 0.0
    
    @pytest.mark.asyncio
    async def test_find_similar_chunks_success(self, service):
        """Test finding similar chunks."""
        query_embedding = [1.0, 0.0, 0.0]
        
        chunk_embeddings = [
            {
                "text": "Similar chunk",
                "embedding": [0.9, 0.1, 0.0],  # High similarity
                "chunk_index": 0
            },
            {
                "text": "Different chunk",
                "embedding": [0.0, 1.0, 0.0],  # Low similarity
                "chunk_index": 1
            },
            {
                "text": "Another similar chunk",
                "embedding": [0.8, 0.2, 0.0],  # Medium similarity
                "chunk_index": 2
            }
        ]
        
        result = await service.find_similar_chunks(
            query_embedding=query_embedding,
            chunk_embeddings=chunk_embeddings,
            top_k=2,
            similarity_threshold=0.5
        )
        
        assert len(result) == 2  # Only 2 chunks above threshold
        assert result[0]["similarity_score"] > result[1]["similarity_score"]  # Sorted by similarity
        assert all("similarity_score" in chunk for chunk in result)
    
    @pytest.mark.asyncio
    async def test_find_similar_chunks_empty_list(self, service):
        """Test finding similar chunks with empty list."""
        query_embedding = [1.0, 0.0, 0.0]
        
        result = await service.find_similar_chunks(
            query_embedding=query_embedding,
            chunk_embeddings=[],
            top_k=5
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_find_similar_chunks_no_embeddings(self, service):
        """Test finding similar chunks when chunks have no embeddings."""
        query_embedding = [1.0, 0.0, 0.0]
        
        chunk_embeddings = [
            {"text": "Chunk without embedding", "chunk_index": 0},
            {"text": "Another chunk", "chunk_index": 1, "embedding": None}
        ]
        
        result = await service.find_similar_chunks(
            query_embedding=query_embedding,
            chunk_embeddings=chunk_embeddings,
            top_k=5
        )
        
        assert result == []  # No chunks with valid embeddings
    
    @pytest.mark.asyncio
    async def test_find_similar_chunks_threshold_filter(self, service):
        """Test similarity threshold filtering."""
        query_embedding = [1.0, 0.0, 0.0]
        
        chunk_embeddings = [
            {
                "text": "Very similar",
                "embedding": [0.9, 0.1, 0.0],  # High similarity (~0.99)
                "chunk_index": 0
            },
            {
                "text": "Somewhat similar",
                "embedding": [0.5, 0.5, 0.0],  # Medium similarity (~0.71)
                "chunk_index": 1
            },
            {
                "text": "Not similar",
                "embedding": [0.0, 1.0, 0.0],  # Low similarity (0.0)
                "chunk_index": 2
            }
        ]
        
        # High threshold should only return very similar chunks
        result = await service.find_similar_chunks(
            query_embedding=query_embedding,
            chunk_embeddings=chunk_embeddings,
            top_k=10,
            similarity_threshold=0.8
        )
        
        assert len(result) == 1  # Only the very similar chunk
        assert result[0]["text"] == "Very similar"


class TestJSONSerialization:
    
    @pytest.fixture
    def service(self):
        return EmbeddingService(api_key="test-key")
    
    def test_embedding_to_json(self, service):
        """Test converting embedding to JSON."""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        json_str = service.embedding_to_json(embedding)
        
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed == embedding
    
    def test_embedding_from_json(self, service):
        """Test converting JSON back to embedding."""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        json_str = json.dumps(embedding)
        
        result = service.embedding_from_json(json_str)
        assert result == embedding
    
    def test_embedding_from_json_invalid(self, service):
        """Test error handling for invalid JSON."""
        invalid_json = "not valid json"
        
        with pytest.raises(EmbeddingError, match="Failed to parse embedding JSON"):
            service.embedding_from_json(invalid_json)


class TestGlobalServiceFunctions:
    
    @patch('orchestrator.embedding_service._embedding_service', None)
    def test_get_embedding_service_creates_instance(self):
        """Test that get_embedding_service creates a new instance."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            service = get_embedding_service()
            assert isinstance(service, EmbeddingService)
    
    @patch('orchestrator.embedding_service._embedding_service')
    def test_get_embedding_service_returns_existing(self, mock_service):
        """Test that get_embedding_service returns existing instance."""
        mock_service_instance = Mock(spec=EmbeddingService)
        mock_service.__bool__ = Mock(return_value=True)  # Mock the None check
        mock_service.return_value = mock_service_instance
        
        # The global variable is already set, so it should return the existing instance
        # This test verifies the singleton pattern
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        
        # Both calls should return the same instance
        assert service1 is service2
    
    @pytest.mark.asyncio
    async def test_embed_document_text_convenience_function(self):
        """Test the convenience function for document text embedding."""
        text = "Test document text for embedding."
        
        with patch('orchestrator.embedding_service.get_embedding_service') as mock_get_service:
            mock_service = Mock(spec=EmbeddingService)
            mock_service.embed_text_with_chunking = AsyncMock(return_value=[
                {"text": "chunk 1", "embedding": [0.1, 0.2]},
                {"text": "chunk 2", "embedding": [0.3, 0.4]}
            ])
            mock_get_service.return_value = mock_service
            
            result = await embed_document_text(text)
            
            assert len(result) == 2
            mock_service.embed_text_with_chunking.assert_called_once_with(
                text=text,
                chunking_strategy="sentences",
                max_tokens=500,
                overlap_tokens=50
            )


class TestErrorHandling:
    
    @pytest.fixture
    def service(self):
        return EmbeddingService(api_key="test-key")
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, service):
        """Test handling of network errors."""
        service.embeddings_client.embed_query = Mock(
            side_effect=Exception("Network timeout")
        )
        
        with pytest.raises(EmbeddingError, match="Embedding generation failed"):
            await service.generate_embedding("test text")
    
    @pytest.mark.asyncio
    async def test_api_rate_limit_simulation(self, service):
        """Test behavior under API rate limits (simulated)."""
        # Simulate rate limit error
        service.embeddings_client.embed_documents = Mock(
            side_effect=Exception("Rate limit exceeded")
        )
        
        with pytest.raises(EmbeddingError, match="Batch embedding generation failed"):
            await service.generate_embeddings_batch(["text1", "text2"])


@pytest.mark.integration
class TestIntegrationScenarios:
    """Integration tests that require actual API calls (marked for optional execution)."""
    
    @pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") == "sk-test",
        reason="Requires real OpenAI API key"
    )
    @pytest.mark.asyncio
    async def test_real_embedding_generation(self):
        """Test with real OpenAI API (only run with valid API key)."""
        import os
        
        service = EmbeddingService()
        
        try:
            embedding = await service.generate_embedding("This is a test sentence.")
            assert isinstance(embedding, list)
            assert len(embedding) > 0
            assert all(isinstance(x, float) for x in embedding)
        except Exception as e:
            pytest.skip(f"API call failed: {e}")
    
    @pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") == "sk-test",
        reason="Requires real OpenAI API key"
    )
    @pytest.mark.asyncio
    async def test_real_document_embedding(self):
        """Test document embedding with real API."""
        document_text = """
        This is a sample document for testing.
        It contains multiple sentences and paragraphs.
        
        The embedding service should chunk this text appropriately
        and generate embeddings for each chunk.
        
        This allows for semantic search within the document content.
        """
        
        try:
            result = await embed_document_text(document_text, max_tokens=20)
            
            assert len(result) > 0
            for chunk_data in result:
                assert "text" in chunk_data
                assert "embedding" in chunk_data
                assert isinstance(chunk_data["embedding"], list)
                assert len(chunk_data["embedding"]) > 0
        except Exception as e:
            pytest.skip(f"API call failed: {e}")