import os
import asyncio
import logging
from typing import List, Optional, Dict, Any
import json

import httpx
from langchain_openai import OpenAIEmbeddings

from orchestrator.text_chunking import TextChunk, chunk_text

logger = logging.getLogger(__name__)

class EmbeddingError(Exception):
    """Exception raised when embedding generation fails."""
    pass

class EmbeddingService:
    """Service for generating and managing text embeddings using OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        """
        Initialize the embedding service.
        
        Args:
            api_key: OpenAI API key (if None, will use OPENAI_API_KEY env var)
            model: Embedding model to use
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise EmbeddingError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.model = model
        self.embeddings_client = OpenAIEmbeddings(
            model=self.model,
            api_key=self.api_key
        )
        
        # Rate limiting and batch settings
        self.max_batch_size = 100  # OpenAI allows up to 2048 inputs per batch
        self.max_retries = 3
        self.retry_delay = 1.0
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot generate embedding for empty text")
        
        try:
            # Use asyncio.to_thread for non-blocking execution
            embedding = await asyncio.to_thread(
                self.embeddings_client.embed_query, 
                text.strip()
            )
            return embedding
        
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingError(f"Embedding generation failed: {str(e)}")
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            return []
        
        # Filter out empty texts
        valid_texts = [text.strip() for text in texts if text and text.strip()]
        if not valid_texts:
            raise EmbeddingError("No valid texts provided for embedding")
        
        embeddings = []
        
        # Process in batches to respect API limits
        for i in range(0, len(valid_texts), self.max_batch_size):
            batch = valid_texts[i:i + self.max_batch_size]
            
            try:
                # Use asyncio.to_thread for non-blocking execution
                batch_embeddings = await asyncio.to_thread(
                    self.embeddings_client.embed_documents,
                    batch
                )
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                raise EmbeddingError(f"Batch embedding generation failed: {str(e)}")
        
        return embeddings
    
    async def embed_text_with_chunking(
        self,
        text: str,
        chunking_strategy: str = "sentences",
        max_tokens: int = 500,
        overlap_tokens: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Embed text after chunking it into smaller pieces.
        
        Args:
            text: Text to chunk and embed
            chunking_strategy: Strategy for chunking ("sentences", "paragraphs", "characters")
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of tokens to overlap between chunks
            
        Returns:
            List of dictionaries containing chunk info and embeddings
            
        Raises:
            EmbeddingError: If chunking or embedding fails
        """
        if not text or not text.strip():
            return []
        
        try:
            # Chunk the text
            chunks = chunk_text(
                text=text,
                strategy=chunking_strategy,
                max_tokens=max_tokens,
                overlap_tokens=overlap_tokens
            )
            
            if not chunks:
                logger.warning("No chunks generated from text")
                return []
            
            logger.info(f"Generated {len(chunks)} chunks for embedding")
            
            # Extract text from chunks for batch embedding
            chunk_texts = [chunk.text for chunk in chunks]
            
            # Generate embeddings for all chunks
            embeddings = await self.generate_embeddings_batch(chunk_texts)
            
            # Combine chunks with their embeddings
            result = []
            for chunk, embedding in zip(chunks, embeddings):
                result.append({
                    "text": chunk.text,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "token_count": chunk.token_count,
                    "embedding": embedding,
                    "embedding_model": self.model
                })
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to embed text with chunking: {e}")
            raise EmbeddingError(f"Text embedding with chunking failed: {str(e)}")
    
    def embedding_to_json(self, embedding: List[float]) -> str:
        """Convert embedding vector to JSON string for database storage."""
        return json.dumps(embedding)
    
    def embedding_from_json(self, embedding_json: str) -> List[float]:
        """Convert JSON string back to embedding vector."""
        try:
            return json.loads(embedding_json)
        except json.JSONDecodeError as e:
            raise EmbeddingError(f"Failed to parse embedding JSON: {e}")
    
    def calculate_cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        if len(embedding1) != len(embedding2):
            raise EmbeddingError("Embeddings must have the same dimensions")
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        
        # Calculate magnitudes
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5
        
        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def find_similar_chunks(
        self,
        query_embedding: List[float],
        chunk_embeddings: List[Dict[str, Any]],
        top_k: int = 5,
        similarity_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Find the most similar chunks to a query embedding.
        
        Args:
            query_embedding: Query embedding vector
            chunk_embeddings: List of chunk dictionaries with embeddings
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score to include
            
        Returns:
            List of similar chunks with similarity scores
        """
        if not chunk_embeddings:
            return []
        
        # Calculate similarities
        similarities = []
        for chunk_data in chunk_embeddings:
            chunk_embedding = chunk_data.get("embedding", [])
            if not chunk_embedding:
                continue
            
            try:
                similarity = self.calculate_cosine_similarity(query_embedding, chunk_embedding)
                if similarity >= similarity_threshold:
                    result = chunk_data.copy()
                    result["similarity_score"] = similarity
                    similarities.append(result)
            except EmbeddingError:
                logger.warning("Skipped chunk due to embedding dimension mismatch")
                continue
        
        # Sort by similarity score (descending) and return top_k
        similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similarities[:top_k]
    
    def get_embedding_info(self) -> Dict[str, Any]:
        """Get information about the current embedding configuration."""
        return {
            "model": self.model,
            "api_key_configured": bool(self.api_key),
            "max_batch_size": self.max_batch_size,
            "max_retries": self.max_retries
        }

# Global embedding service instance
_embedding_service: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

async def embed_document_text(
    text: str,
    chunking_strategy: str = "sentences",
    max_tokens: int = 500,
    overlap_tokens: int = 50
) -> List[Dict[str, Any]]:
    """
    Convenience function to embed document text with chunking.
    
    Args:
        text: Document text to embed
        chunking_strategy: Strategy for chunking
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Number of tokens to overlap
        
    Returns:
        List of chunk embeddings
    """
    service = get_embedding_service()
    return await service.embed_text_with_chunking(
        text=text,
        chunking_strategy=chunking_strategy,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens
    )