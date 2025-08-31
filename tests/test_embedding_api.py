import pytest
import json
from unittest.mock import patch, Mock, AsyncMock
from fastapi.testclient import TestClient
from api.main import app
from orchestrator import crud


client = TestClient(app)


class TestDocumentUploadWithEmbeddings:
    
    def setup_method(self):
        """Set up test environment."""
        crud.init_db()
        # Create a test project
        self.project = crud.create_project("Test Project", "Test description")
    
    def test_upload_document_generates_embeddings(self):
        """Test that document upload generates embeddings."""
        # Mock the embedding service
        with patch('orchestrator.embedding_service.embed_document_text') as mock_embed:
            mock_embed.return_value = [
                {
                    "text": "Test content chunk 1",
                    "chunk_index": 0,
                    "start_char": 0,
                    "end_char": 21,
                    "token_count": 5,
                    "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "embedding_model": "text-embedding-3-small"
                },
                {
                    "text": "Test content chunk 2",
                    "chunk_index": 1,
                    "start_char": 22,
                    "end_char": 43,
                    "token_count": 5,
                    "embedding": [0.6, 0.7, 0.8, 0.9, 1.0],
                    "embedding_model": "text-embedding-3-small"
                }
            ]
            
            # Upload a text document
            files = {"file": ("test.txt", "Test content chunk 1. Test content chunk 2.", "text/plain")}
            response = client.post(f"/projects/{self.project.id}/documents", files=files)
            
            assert response.status_code == 201
            document_data = response.json()
            
            # Verify document was created
            assert document_data["filename"] == "test.txt"
            assert document_data["project_id"] == self.project.id
            
            # Verify embeddings were generated
            mock_embed.assert_called_once()
            
            # Verify chunks were stored in database
            chunks = crud.get_document_chunks(document_data["id"])
            assert len(chunks) == 2
            
            for i, chunk in enumerate(chunks):
                assert chunk["text"] == f"Test content chunk {i + 1}"
                assert chunk["embedding"] is not None
                assert chunk["embedding_model"] == "text-embedding-3-small"
    
    def test_upload_document_embedding_failure_doesnt_fail_upload(self):
        """Test that embedding failure doesn't prevent document upload."""
        with patch('orchestrator.embedding_service.embed_document_text') as mock_embed:
            # Mock embedding failure
            mock_embed.side_effect = Exception("Embedding API failed")
            
            files = {"file": ("test.txt", "Test content", "text/plain")}
            response = client.post(f"/projects/{self.project.id}/documents", files=files)
            
            # Upload should still succeed
            assert response.status_code == 201
            document_data = response.json()
            
            # Document should be created without embeddings
            assert document_data["filename"] == "test.txt"
            
            # No chunks should be stored
            chunks = crud.get_document_chunks(document_data["id"])
            assert len(chunks) == 0
    
    def test_upload_unsupported_file_format(self):
        """Test uploading unsupported file format."""
        files = {"file": ("test.unknown", b"binary content", "application/octet-stream")}
        response = client.post(f"/projects/{self.project.id}/documents", files=files)
        
        assert response.status_code == 422
        assert "Document parsing failed" in response.json()["detail"]


class TestDocumentChunksAPI:
    
    def setup_method(self):
        """Set up test environment."""
        crud.init_db()
        self.project = crud.create_project("Test Project", "Test description")
        self.document = crud.create_document(
            self.project.id,
            "test.txt",
            "Test document content",
            None
        )
        
        # Create test chunks
        self.chunks_data = [
            {
                "text": "First chunk of text",
                "chunk_index": 0,
                "start_char": 0,
                "end_char": 19,
                "token_count": 4,
                "embedding": [0.1, 0.2, 0.3],
                "embedding_model": "text-embedding-3-small"
            },
            {
                "text": "Second chunk of text",
                "chunk_index": 1,
                "start_char": 20,
                "end_char": 40,
                "token_count": 4,
                "embedding": [0.4, 0.5, 0.6],
                "embedding_model": "text-embedding-3-small"
            }
        ]
        crud.create_document_chunks(self.document.id, self.chunks_data)
    
    def test_get_document_chunks(self):
        """Test retrieving chunks for a document."""
        response = client.get(f"/documents/{self.document.id}/chunks")
        
        assert response.status_code == 200
        chunks = response.json()
        
        assert len(chunks) == 2
        for i, chunk in enumerate(chunks):
            assert chunk["text"] == self.chunks_data[i]["text"]
            assert chunk["chunk_index"] == i
            assert chunk["embedding"] is not None
    
    def test_get_document_chunks_nonexistent_document(self):
        """Test retrieving chunks for nonexistent document."""
        response = client.get("/documents/99999/chunks")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "document not found"
    
    def test_get_document_chunks_no_chunks(self):
        """Test retrieving chunks when document has no chunks."""
        # Create document without chunks
        doc = crud.create_document(self.project.id, "empty.txt", "Empty doc", None)
        
        response = client.get(f"/documents/{doc.id}/chunks")
        
        assert response.status_code == 200
        assert response.json() == []


class TestSemanticSearchAPI:
    
    def setup_method(self):
        """Set up test environment with documents and embeddings."""
        crud.init_db()
        self.project = crud.create_project("Search Test Project", "Test description")
        
        # Create test documents with chunks
        doc1 = crud.create_document(self.project.id, "doc1.txt", "Technology content", None)
        doc2 = crud.create_document(self.project.id, "doc2.txt", "Business content", None)
        
        # Create chunks with embeddings for semantic similarity
        tech_chunks = [
            {
                "text": "Artificial intelligence and machine learning",
                "chunk_index": 0,
                "token_count": 5,
                "embedding": [0.9, 0.1, 0.0],  # High similarity to tech query
                "embedding_model": "text-embedding-3-small"
            },
            {
                "text": "Python programming and software development",
                "chunk_index": 1,
                "token_count": 5,
                "embedding": [0.8, 0.2, 0.0],  # Medium-high similarity to tech query
                "embedding_model": "text-embedding-3-small"
            }
        ]
        
        business_chunks = [
            {
                "text": "Marketing strategies and customer engagement",
                "chunk_index": 0,
                "token_count": 5,
                "embedding": [0.1, 0.9, 0.0],  # Low similarity to tech query
                "embedding_model": "text-embedding-3-small"
            },
            {
                "text": "Financial planning and budget management",
                "chunk_index": 1,
                "token_count": 5,
                "embedding": [0.0, 0.8, 0.2],  # Low similarity to tech query
                "embedding_model": "text-embedding-3-small"
            }
        ]
        
        crud.create_document_chunks(doc1.id, tech_chunks)
        crud.create_document_chunks(doc2.id, business_chunks)
    
    def test_semantic_search_success(self):
        """Test successful semantic search."""
        # Mock the embedding service to return a tech-oriented query embedding
        with patch('orchestrator.embedding_service.get_embedding_service') as mock_get_service:
            mock_service = Mock()
            mock_service.generate_embedding = AsyncMock(
                return_value=[1.0, 0.0, 0.0]  # Tech-oriented query embedding
            )
            mock_service.find_similar_chunks = AsyncMock(
                return_value=[
                    {
                        "text": "Artificial intelligence and machine learning",
                        "chunk_index": 0,
                        "embedding": [0.9, 0.1, 0.0],
                        "similarity_score": 0.99,
                        "doc_id": 1,
                        "filename": "doc1.txt"
                    },
                    {
                        "text": "Python programming and software development",
                        "chunk_index": 1,
                        "embedding": [0.8, 0.2, 0.0],
                        "similarity_score": 0.89,
                        "doc_id": 1,
                        "filename": "doc1.txt"
                    }
                ]
            )
            mock_get_service.return_value = mock_service
            
            query_data = {
                "query": "machine learning algorithms",
                "limit": 5,
                "similarity_threshold": 0.3
            }
            
            response = client.post(f"/projects/{self.project.id}/search", json=query_data)
            
            assert response.status_code == 200
            result = response.json()
            
            assert result["query"] == "machine learning algorithms"
            assert len(result["results"]) == 2
            assert result["total_chunks"] == 4  # 2 from each document
            
            # Results should be sorted by similarity score
            assert result["results"][0]["similarity_score"] >= result["results"][1]["similarity_score"]
            
            # Verify API calls
            mock_service.generate_embedding.assert_called_once_with("machine learning algorithms")
            mock_service.find_similar_chunks.assert_called_once()
    
    def test_semantic_search_empty_query(self):
        """Test search with empty query."""
        query_data = {"query": ""}
        
        response = client.post(f"/projects/{self.project.id}/search", json=query_data)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Query text is required"
    
    def test_semantic_search_missing_query(self):
        """Test search with missing query field."""
        query_data = {"limit": 5}
        
        response = client.post(f"/projects/{self.project.id}/search", json=query_data)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Query text is required"
    
    def test_semantic_search_nonexistent_project(self):
        """Test search for nonexistent project."""
        query_data = {"query": "test query"}
        
        response = client.post("/projects/99999/search", json=query_data)
        
        assert response.status_code == 404
        assert response.json()["detail"] == "project not found"
    
    def test_semantic_search_no_chunks(self):
        """Test search in project with no document chunks."""
        empty_project = crud.create_project("Empty Project", "No documents")
        
        with patch('orchestrator.embedding_service.get_embedding_service') as mock_get_service:
            mock_service = Mock()
            mock_service.generate_embedding = AsyncMock(return_value=[1.0, 0.0, 0.0])
            mock_get_service.return_value = mock_service
            
            query_data = {"query": "test query"}
            
            response = client.post(f"/projects/{empty_project.id}/search", json=query_data)
            
            assert response.status_code == 200
            result = response.json()
            
            assert result["query"] == "test query"
            assert result["results"] == []
            assert result["total_chunks"] == 0
    
    def test_semantic_search_embedding_error(self):
        """Test search when embedding generation fails."""
        with patch('orchestrator.embedding_service.get_embedding_service') as mock_get_service:
            mock_service = Mock()
            mock_service.generate_embedding = AsyncMock(
                side_effect=Exception("OpenAI API error")
            )
            mock_get_service.return_value = mock_service
            
            query_data = {"query": "test query"}
            
            response = client.post(f"/projects/{self.project.id}/search", json=query_data)
            
            assert response.status_code == 500
            assert "Search failed" in response.json()["detail"]
    
    def test_semantic_search_custom_parameters(self):
        """Test search with custom parameters."""
        with patch('orchestrator.embedding_service.get_embedding_service') as mock_get_service:
            mock_service = Mock()
            mock_service.generate_embedding = AsyncMock(return_value=[1.0, 0.0, 0.0])
            mock_service.find_similar_chunks = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service
            
            query_data = {
                "query": "custom query",
                "limit": 10,
                "similarity_threshold": 0.7
            }
            
            response = client.post(f"/projects/{self.project.id}/search", json=query_data)
            
            assert response.status_code == 200
            result = response.json()
            
            assert result["similarity_threshold"] == 0.7
            
            # Verify parameters were passed to the service
            mock_service.find_similar_chunks.assert_called_once()
            call_args = mock_service.find_similar_chunks.call_args
            assert call_args.kwargs["top_k"] == 10
            assert call_args.kwargs["similarity_threshold"] == 0.7


class TestEmbeddingIntegration:
    """Test the full integration flow from document upload to search."""
    
    def setup_method(self):
        """Set up integration test environment."""
        crud.init_db()
        self.project = crud.create_project("Integration Project", "Full integration test")
    
    def test_full_integration_flow(self):
        """Test the complete flow: upload -> embed -> search."""
        # Mock embedding service for consistent results
        with patch('orchestrator.embedding_service.embed_document_text') as mock_embed:
            # Mock document embedding
            mock_embed.return_value = [
                {
                    "text": "The artificial intelligence revolution is transforming technology.",
                    "chunk_index": 0,
                    "token_count": 8,
                    "embedding": [0.9, 0.1, 0.0, 0.0, 0.0],
                    "embedding_model": "text-embedding-3-small"
                },
                {
                    "text": "Machine learning algorithms are becoming more sophisticated.",
                    "chunk_index": 1,
                    "token_count": 7,
                    "embedding": [0.8, 0.2, 0.0, 0.0, 0.0],
                    "embedding_model": "text-embedding-3-small"
                }
            ]
            
            # 1. Upload document
            document_content = (
                "The artificial intelligence revolution is transforming technology. "
                "Machine learning algorithms are becoming more sophisticated."
            )
            files = {"file": ("ai_doc.txt", document_content, "text/plain")}
            upload_response = client.post(f"/projects/{self.project.id}/documents", files=files)
            
            assert upload_response.status_code == 201
            document = upload_response.json()
            
            # 2. Verify chunks were created
            chunks_response = client.get(f"/documents/{document['id']}/chunks")
            assert chunks_response.status_code == 200
            chunks = chunks_response.json()
            assert len(chunks) == 2
            
            # 3. Mock search embedding service
            with patch('orchestrator.embedding_service.get_embedding_service') as mock_get_service:
                mock_service = Mock()
                mock_service.generate_embedding = AsyncMock(
                    return_value=[1.0, 0.0, 0.0, 0.0, 0.0]  # Similar to AI content
                )
                
                # Mock similarity search to return relevant chunks
                mock_service.find_similar_chunks = AsyncMock(
                    return_value=[
                        {
                            "text": "The artificial intelligence revolution is transforming technology.",
                            "chunk_index": 0,
                            "embedding": [0.9, 0.1, 0.0, 0.0, 0.0],
                            "similarity_score": 0.95,
                            "doc_id": document["id"],
                            "filename": "ai_doc.txt"
                        }
                    ]
                )
                mock_get_service.return_value = mock_service
                
                # 4. Perform semantic search
                search_query = {"query": "artificial intelligence technology"}
                search_response = client.post(f"/projects/{self.project.id}/search", json=search_query)
                
                assert search_response.status_code == 200
                search_results = search_response.json()
                
                assert search_results["query"] == "artificial intelligence technology"
                assert len(search_results["results"]) == 1
                assert search_results["results"][0]["similarity_score"] == 0.95
                assert "artificial intelligence" in search_results["results"][0]["text"]
    
    def test_multiple_documents_search(self):
        """Test search across multiple documents."""
        # Mock embeddings for multiple documents
        with patch('orchestrator.embedding_service.embed_document_text') as mock_embed:
            # First document (AI/Tech focused)
            mock_embed.return_value = [
                {
                    "text": "Artificial intelligence and deep learning",
                    "chunk_index": 0,
                    "token_count": 5,
                    "embedding": [0.9, 0.1, 0.0],
                    "embedding_model": "text-embedding-3-small"
                }
            ]
            
            # Upload first document
            files1 = {"file": ("tech.txt", "Artificial intelligence and deep learning", "text/plain")}
            client.post(f"/projects/{self.project.id}/documents", files=files1)
            
            # Second document (Business focused)
            mock_embed.return_value = [
                {
                    "text": "Business strategy and market analysis",
                    "chunk_index": 0,
                    "token_count": 5,
                    "embedding": [0.1, 0.9, 0.0],
                    "embedding_model": "text-embedding-3-small"
                }
            ]
            
            # Upload second document
            files2 = {"file": ("business.txt", "Business strategy and market analysis", "text/plain")}
            client.post(f"/projects/{self.project.id}/documents", files=files2)
            
            # Mock search to return results from both documents
            with patch('orchestrator.embedding_service.get_embedding_service') as mock_get_service:
                mock_service = Mock()
                mock_service.generate_embedding = AsyncMock(return_value=[0.5, 0.5, 0.0])
                mock_service.find_similar_chunks = AsyncMock(
                    return_value=[
                        {
                            "text": "Artificial intelligence and deep learning",
                            "similarity_score": 0.7,
                            "filename": "tech.txt"
                        },
                        {
                            "text": "Business strategy and market analysis",
                            "similarity_score": 0.6,
                            "filename": "business.txt"
                        }
                    ]
                )
                mock_get_service.return_value = mock_service
                
                # Search should find relevant content from both documents
                query_data = {"query": "strategic analysis"}
                response = client.post(f"/projects/{self.project.id}/search", json=query_data)
                
                assert response.status_code == 200
                results = response.json()
                
                assert len(results["results"]) == 2
                assert results["total_chunks"] == 2
                
                # Results should be sorted by similarity
                assert results["results"][0]["similarity_score"] >= results["results"][1]["similarity_score"]