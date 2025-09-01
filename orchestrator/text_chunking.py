import re
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    text: str
    chunk_index: int
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    token_count: Optional[int] = None

def estimate_token_count(text: str) -> int:
    """
    Estimate token count using a simple heuristic.
    Approximation: 1 token ≈ 4 characters for English text.
    This is a rough estimate; actual tokenization may vary.
    """
    return len(text) // 4

def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex patterns.
    Handles common sentence endings while avoiding false positives.
    """
    # Pattern to match sentence endings, avoiding common abbreviations
    sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+'
    sentences = re.split(sentence_pattern, text.strip())
    
    # Clean up empty sentences and whitespace
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

def chunk_by_tokens(
    text: str,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
    respect_sentence_boundaries: bool = True
) -> List[TextChunk]:
    """
    Chunk text by token count with optional sentence boundary respect.
    
    Args:
        text: The text to chunk
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Number of tokens to overlap between chunks
        respect_sentence_boundaries: Whether to respect sentence boundaries
        
    Returns:
        List of TextChunk objects
    """
    if not text or not text.strip():
        return []
    
    chunks = []
    
    if respect_sentence_boundaries:
        sentences = split_into_sentences(text)
        if not sentences:
            # Fallback to character-based if no sentences found
            return chunk_by_characters(text, max_tokens * 4, overlap_tokens * 4)
        
        current_chunk = ""
        current_tokens = 0
        chunk_start = 0
        
        for sentence in sentences:
            sentence_tokens = estimate_token_count(sentence)
            
            # If single sentence exceeds max_tokens, split it
            if sentence_tokens > max_tokens:
                # Save current chunk if it exists
                if current_chunk:
                    chunk_text = current_chunk.strip()
                    chunks.append(TextChunk(
                        text=chunk_text,
                        chunk_index=len(chunks),
                        start_char=chunk_start,
                        end_char=chunk_start + len(chunk_text),
                        token_count=current_tokens
                    ))
                    current_chunk = ""
                    current_tokens = 0
                    chunk_start = chunk_start + len(chunk_text)
                
                # Split long sentence into smaller chunks
                long_sentence_chunks = chunk_by_characters(
                    sentence, max_tokens * 4, overlap_tokens * 4
                )
                for long_chunk in long_sentence_chunks:
                    long_chunk.chunk_index = len(chunks)
                    chunks.append(long_chunk)
                    chunk_start += len(long_chunk.text)
                continue
            
            # Check if adding this sentence would exceed max_tokens
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunk_text = current_chunk.strip()
                chunks.append(TextChunk(
                    text=chunk_text,
                    chunk_index=len(chunks),
                    start_char=chunk_start,
                    end_char=chunk_start + len(chunk_text),
                    token_count=current_tokens
                ))
                
                # Start new chunk with overlap if specified
                if overlap_tokens > 0 and chunks:
                    overlap_text = get_overlap_text(chunk_text, overlap_tokens)
                    current_chunk = overlap_text + " " + sentence
                    current_tokens = estimate_token_count(current_chunk)
                else:
                    current_chunk = sentence
                    current_tokens = sentence_tokens
                
                chunk_start = chunk_start + len(chunk_text) - len(overlap_text) if overlap_tokens > 0 else chunk_start + len(chunk_text)
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_tokens += sentence_tokens
        
        # Add final chunk if it exists
        if current_chunk:
            chunk_text = current_chunk.strip()
            chunks.append(TextChunk(
                text=chunk_text,
                chunk_index=len(chunks),
                start_char=chunk_start,
                end_char=chunk_start + len(chunk_text),
                token_count=current_tokens
            ))
    
    else:
        # Simple character-based chunking without sentence boundaries
        return chunk_by_characters(text, max_tokens * 4, overlap_tokens * 4)
    
    return chunks

def chunk_by_characters(
    text: str,
    max_chars: int = 2000,
    overlap_chars: int = 200
) -> List[TextChunk]:
    """
    Chunk text by character count.
    
    Args:
        text: The text to chunk
        max_chars: Maximum characters per chunk
        overlap_chars: Number of characters to overlap between chunks
        
    Returns:
        List of TextChunk objects
    """
    if not text or not text.strip():
        return []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk_text = text[start:end].strip()
        
        if chunk_text:
            chunks.append(TextChunk(
                text=chunk_text,
                chunk_index=len(chunks),
                start_char=start,
                end_char=end,
                token_count=estimate_token_count(chunk_text)
            ))
        
        # Move start position considering overlap
        if end >= len(text):
            break
        start = end - overlap_chars
        if start <= 0:
            start = end
    
    return chunks

def chunk_by_paragraphs(
    text: str,
    max_tokens: int = 500,
    overlap_tokens: int = 50
) -> List[TextChunk]:
    """
    Chunk text by paragraphs, combining paragraphs until max_tokens is reached.
    
    Args:
        text: The text to chunk
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Number of tokens to overlap between chunks
        
    Returns:
        List of TextChunk objects
    """
    if not text or not text.strip():
        return []
    
    # Split by double newlines (paragraph separators)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    if not paragraphs:
        # Fallback to sentence-based chunking
        return chunk_by_tokens(text, max_tokens, overlap_tokens)
    
    chunks = []
    current_chunk = ""
    current_tokens = 0
    chunk_start = 0
    
    for paragraph in paragraphs:
        paragraph_tokens = estimate_token_count(paragraph)
        
        # If single paragraph exceeds max_tokens, split it
        if paragraph_tokens > max_tokens:
            # Save current chunk if it exists
            if current_chunk:
                chunk_text = current_chunk.strip()
                chunks.append(TextChunk(
                    text=chunk_text,
                    chunk_index=len(chunks),
                    start_char=chunk_start,
                    end_char=chunk_start + len(chunk_text),
                    token_count=current_tokens
                ))
                current_chunk = ""
                current_tokens = 0
                chunk_start += len(chunk_text)
            
            # Split long paragraph
            para_chunks = chunk_by_tokens(paragraph, max_tokens, overlap_tokens)
            for para_chunk in para_chunks:
                para_chunk.chunk_index = len(chunks)
                chunks.append(para_chunk)
                chunk_start += len(para_chunk.text)
            continue
        
        # Check if adding this paragraph would exceed max_tokens
        if current_tokens + paragraph_tokens > max_tokens and current_chunk:
            # Save current chunk
            chunk_text = current_chunk.strip()
            chunks.append(TextChunk(
                text=chunk_text,
                chunk_index=len(chunks),
                start_char=chunk_start,
                end_char=chunk_start + len(chunk_text),
                token_count=current_tokens
            ))
            
            # Start new chunk with overlap if specified
            if overlap_tokens > 0 and chunks:
                overlap_text = get_overlap_text(chunk_text, overlap_tokens)
                current_chunk = overlap_text + "\n\n" + paragraph
                current_tokens = estimate_token_count(current_chunk)
            else:
                current_chunk = paragraph
                current_tokens = paragraph_tokens
            
            chunk_start += len(chunk_text) - len(overlap_text) if overlap_tokens > 0 else len(chunk_text)
        else:
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
            current_tokens += paragraph_tokens
    
    # Add final chunk if it exists
    if current_chunk:
        chunk_text = current_chunk.strip()
        chunks.append(TextChunk(
            text=chunk_text,
            chunk_index=len(chunks),
            start_char=chunk_start,
            end_char=chunk_start + len(chunk_text),
            token_count=current_tokens
        ))
    
    return chunks

def get_overlap_text(text: str, overlap_tokens: int) -> str:
    """
    Get the last portion of text for overlap, respecting word boundaries.
    
    Args:
        text: The source text
        overlap_tokens: Number of tokens to overlap
        
    Returns:
        Overlap text string
    """
    if not text or overlap_tokens <= 0:
        return ""
    
    words = text.split()
    if not words:
        return ""
    
    # Estimate words needed for overlap_tokens (rough estimate: 1.3 words per token)
    overlap_words = min(int(overlap_tokens * 1.3), len(words))
    
    if overlap_words <= 0:
        return ""
    
    return " ".join(words[-overlap_words:])

def chunk_text(
    text: str,
    strategy: str = "sentences",
    max_tokens: int = 500,
    overlap_tokens: int = 50
) -> List[TextChunk]:
    """
    Main chunking function that supports different strategies.
    
    Args:
        text: The text to chunk
        strategy: Chunking strategy ("sentences", "paragraphs", "characters")
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Number of tokens to overlap between chunks
        
    Returns:
        List of TextChunk objects
    """
    if not text or not text.strip():
        return []
    
    if strategy == "paragraphs":
        return chunk_by_paragraphs(text, max_tokens, overlap_tokens)
    elif strategy == "characters":
        return chunk_by_characters(text, max_tokens * 4, overlap_tokens * 4)
    else:  # Default to sentences
        return chunk_by_tokens(text, max_tokens, overlap_tokens, respect_sentence_boundaries=True)

def get_chunking_stats(chunks: List[TextChunk]) -> dict:
    """
    Get statistics about the chunking results.
    
    Args:
        chunks: List of TextChunk objects
        
    Returns:
        Dictionary with chunking statistics
    """
    if not chunks:
        return {
            "total_chunks": 0,
            "total_tokens": 0,
            "avg_tokens_per_chunk": 0,
            "min_tokens": 0,
            "max_tokens": 0
        }
    
    token_counts = [chunk.token_count or 0 for chunk in chunks]
    
    return {
        "total_chunks": len(chunks),
        "total_tokens": sum(token_counts),
        "avg_tokens_per_chunk": sum(token_counts) / len(chunks),
        "min_tokens": min(token_counts),
        "max_tokens": max(token_counts)
    }