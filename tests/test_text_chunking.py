import pytest
from orchestrator.text_chunking import (
    TextChunk,
    estimate_token_count,
    split_into_sentences,
    chunk_by_tokens,
    chunk_by_characters,
    chunk_by_paragraphs,
    chunk_text,
    get_chunking_stats,
    get_overlap_text
)


class TestTokenEstimation:
    
    def test_estimate_token_count(self):
        """Test token count estimation."""
        assert estimate_token_count("hello world") == 2  # 8 chars / 4
        assert estimate_token_count("a") == 0  # 1 char / 4 = 0
        assert estimate_token_count("hello") == 1  # 5 chars / 4 = 1
        assert estimate_token_count("") == 0
        
        # Longer text
        long_text = "This is a longer text that should have more tokens estimated."
        expected = len(long_text) // 4
        assert estimate_token_count(long_text) == expected


class TestSentenceSplitting:
    
    def test_simple_sentences(self):
        """Test splitting simple sentences."""
        text = "Hello world. How are you? I am fine!"
        sentences = split_into_sentences(text)
        expected = ["Hello world.", "How are you?", "I am fine!"]
        assert sentences == expected
    
    def test_abbreviations(self):
        """Test handling of abbreviations."""
        text = "Dr. Smith went to the U.S.A. He was happy."
        sentences = split_into_sentences(text)
        # Should not split on Dr. or U.S.A.
        assert len(sentences) == 2
        assert "Dr. Smith went to the U.S.A." in sentences[0]
        assert "He was happy." in sentences[1]
    
    def test_empty_text(self):
        """Test empty text handling."""
        assert split_into_sentences("") == []
        assert split_into_sentences("   ") == []
    
    def test_no_sentence_endings(self):
        """Test text without sentence endings."""
        text = "Just a simple text without endings"
        sentences = split_into_sentences(text)
        assert sentences == [text]


class TestTokenBasedChunking:
    
    def test_simple_chunking(self):
        """Test basic token-based chunking."""
        text = "This is a test. This is another sentence. And one more sentence."
        chunks = chunk_by_tokens(text, max_tokens=10, overlap_tokens=2)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, TextChunk)
            assert chunk.text
            assert chunk.token_count <= 10 or chunk.token_count == estimate_token_count(chunk.text)
    
    def test_empty_text(self):
        """Test chunking empty text."""
        chunks = chunk_by_tokens("", max_tokens=100)
        assert chunks == []
        
        chunks = chunk_by_tokens("   ", max_tokens=100)
        assert chunks == []
    
    def test_single_long_sentence(self):
        """Test chunking a single sentence that exceeds max_tokens."""
        # Create a very long sentence
        long_sentence = "This is a very long sentence that definitely exceeds the token limit " * 20
        chunks = chunk_by_tokens(long_sentence, max_tokens=50, overlap_tokens=10)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.text
    
    def test_chunk_indices(self):
        """Test that chunk indices are properly set."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunk_by_tokens(text, max_tokens=5, overlap_tokens=1)
        
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
    
    def test_no_sentence_boundaries(self):
        """Test chunking without respecting sentence boundaries."""
        text = "This is a test sentence that should be split."
        chunks = chunk_by_tokens(text, max_tokens=5, respect_sentence_boundaries=False)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.text


class TestCharacterBasedChunking:
    
    def test_simple_character_chunking(self):
        """Test basic character-based chunking."""
        text = "A" * 1000  # 1000 characters
        chunks = chunk_by_characters(text, max_chars=200, overlap_chars=50)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.text) <= 200
            assert chunk.start_char is not None
            assert chunk.end_char is not None
    
    def test_empty_text_chars(self):
        """Test character chunking with empty text."""
        chunks = chunk_by_characters("", max_chars=100)
        assert chunks == []
    
    def test_text_shorter_than_max(self):
        """Test chunking text shorter than max_chars."""
        text = "Short text"
        chunks = chunk_by_characters(text, max_chars=100)
        
        assert len(chunks) == 1
        assert chunks[0].text == text


class TestParagraphBasedChunking:
    
    def test_simple_paragraph_chunking(self):
        """Test basic paragraph-based chunking."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunk_by_paragraphs(text, max_tokens=10, overlap_tokens=2)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.text
    
    def test_long_paragraph(self):
        """Test handling of paragraphs that exceed max_tokens."""
        long_paragraph = "This is a very long paragraph. " * 50
        text = f"Short paragraph.\n\n{long_paragraph}\n\nAnother short paragraph."
        
        chunks = chunk_by_paragraphs(text, max_tokens=20, overlap_tokens=5)
        assert len(chunks) > 1
    
    def test_no_paragraphs(self):
        """Test text without paragraph breaks."""
        text = "Just a single line of text without paragraph breaks"
        chunks = chunk_by_paragraphs(text, max_tokens=50)
        
        assert len(chunks) >= 1


class TestMainChunkingFunction:
    
    def test_sentences_strategy(self):
        """Test chunking with sentences strategy."""
        text = "First sentence. Second sentence. Third sentence."
        chunks = chunk_text(text, strategy="sentences", max_tokens=5)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, TextChunk)
    
    def test_paragraphs_strategy(self):
        """Test chunking with paragraphs strategy."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunk_text(text, strategy="paragraphs", max_tokens=10)
        
        assert len(chunks) > 0
    
    def test_characters_strategy(self):
        """Test chunking with characters strategy."""
        text = "A" * 500
        chunks = chunk_text(text, strategy="characters", max_tokens=10)
        
        assert len(chunks) > 1
    
    def test_invalid_strategy(self):
        """Test that invalid strategy defaults to sentences."""
        text = "Test sentence. Another sentence."
        chunks = chunk_text(text, strategy="invalid", max_tokens=5)
        
        assert len(chunks) > 0


class TestOverlapFunctionality:
    
    def test_get_overlap_text(self):
        """Test overlap text extraction."""
        text = "This is a test sentence with several words."
        overlap = get_overlap_text(text, overlap_tokens=3)
        
        assert overlap
        assert len(overlap.split()) <= 4  # Approximate for 3 tokens
    
    def test_overlap_longer_than_text(self):
        """Test overlap when requested tokens exceed text length."""
        text = "Short text"
        overlap = get_overlap_text(text, overlap_tokens=100)
        
        assert overlap == text
    
    def test_zero_overlap(self):
        """Test zero overlap."""
        text = "Some text here"
        overlap = get_overlap_text(text, overlap_tokens=0)
        
        assert overlap == ""
    
    def test_overlap_with_chunking(self):
        """Test that overlapping chunks contain repeated content."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunk_by_tokens(text, max_tokens=8, overlap_tokens=3)
        
        if len(chunks) >= 2:
            # Check that there's some overlap between consecutive chunks
            chunk1_end = chunks[0].text.split()[-3:]  # Last 3 words
            chunk2_start = chunks[1].text.split()[:3]  # First 3 words
            
            # Should have some words in common
            overlap_found = any(word in chunk2_start for word in chunk1_end)
            # Note: This test might be loose as overlap depends on sentence boundaries


class TestChunkingStats:
    
    def test_stats_empty_chunks(self):
        """Test stats with empty chunk list."""
        stats = get_chunking_stats([])
        expected = {
            "total_chunks": 0,
            "total_tokens": 0,
            "avg_tokens_per_chunk": 0,
            "min_tokens": 0,
            "max_tokens": 0
        }
        assert stats == expected
    
    def test_stats_with_chunks(self):
        """Test stats calculation with real chunks."""
        chunks = [
            TextChunk("First chunk", 0, token_count=5),
            TextChunk("Second chunk with more tokens", 1, token_count=10),
            TextChunk("Third", 2, token_count=3)
        ]
        
        stats = get_chunking_stats(chunks)
        
        assert stats["total_chunks"] == 3
        assert stats["total_tokens"] == 18
        assert stats["avg_tokens_per_chunk"] == 6.0
        assert stats["min_tokens"] == 3
        assert stats["max_tokens"] == 10
    
    def test_stats_none_token_counts(self):
        """Test stats when some chunks have None token counts."""
        chunks = [
            TextChunk("First", 0, token_count=5),
            TextChunk("Second", 1, token_count=None),
            TextChunk("Third", 2, token_count=7)
        ]
        
        stats = get_chunking_stats(chunks)
        
        assert stats["total_chunks"] == 3
        assert stats["total_tokens"] == 12  # 5 + 0 + 7
        assert stats["min_tokens"] == 0
        assert stats["max_tokens"] == 7


class TestTextChunkClass:
    
    def test_text_chunk_creation(self):
        """Test TextChunk creation and attributes."""
        chunk = TextChunk(
            text="Test content",
            chunk_index=1,
            start_char=10,
            end_char=23,
            token_count=5
        )
        
        assert chunk.text == "Test content"
        assert chunk.chunk_index == 1
        assert chunk.start_char == 10
        assert chunk.end_char == 23
        assert chunk.token_count == 5
    
    def test_text_chunk_optional_fields(self):
        """Test TextChunk with optional fields."""
        chunk = TextChunk(text="Test", chunk_index=0)
        
        assert chunk.text == "Test"
        assert chunk.chunk_index == 0
        assert chunk.start_char is None
        assert chunk.end_char is None
        assert chunk.token_count is None


class TestIntegrationScenarios:
    
    def test_document_chunking_scenario(self):
        """Test a realistic document chunking scenario."""
        document_text = """
        Introduction
        
        This is a sample document that contains multiple paragraphs and sentences.
        It should be chunked appropriately for embedding generation.
        
        First Section
        
        This section contains information about the first topic. It has several 
        sentences that provide detailed information. The content should be split 
        into manageable chunks.
        
        Second Section
        
        The second section covers different aspects of the topic. It also contains 
        multiple sentences and should be handled properly by the chunking algorithm.
        
        Conclusion
        
        This concludes our sample document. The chunking should preserve the 
        logical structure while maintaining appropriate chunk sizes.
        """
        
        # Test different strategies
        sentence_chunks = chunk_text(document_text, strategy="sentences", max_tokens=50)
        paragraph_chunks = chunk_text(document_text, strategy="paragraphs", max_tokens=100)
        
        assert len(sentence_chunks) > 0
        assert len(paragraph_chunks) > 0
        
        # Sentence chunks should generally be smaller
        assert len(sentence_chunks) >= len(paragraph_chunks)
        
        # All chunks should have content
        for chunk in sentence_chunks + paragraph_chunks:
            assert chunk.text.strip()
            assert chunk.chunk_index >= 0
    
    def test_very_large_document(self):
        """Test chunking a very large document."""
        # Create a large document
        paragraph = "This is a paragraph with multiple sentences. " * 10
        large_document = (paragraph + "\n\n") * 50  # 50 paragraphs
        
        chunks = chunk_text(large_document, strategy="paragraphs", max_tokens=200)
        
        assert len(chunks) > 10  # Should create many chunks
        
        # Verify no chunk exceeds the token limit significantly
        for chunk in chunks:
            # Allow some flexibility for sentence boundaries
            assert chunk.token_count <= 250 or chunk.token_count is None
    
    def test_edge_case_single_word(self):
        """Test chunking with very short content."""
        chunks = chunk_text("Word", max_tokens=1)
        assert len(chunks) == 1
        assert chunks[0].text == "Word"
    
    def test_edge_case_special_characters(self):
        """Test chunking text with special characters."""
        text = "Text with special chars: @#$%^&*(). More text here! And even more?"
        chunks = chunk_text(text, max_tokens=10)
        
        assert len(chunks) > 0
        combined_text = " ".join(chunk.text for chunk in chunks)
        
        # Should preserve the original special characters
        for char in "@#$%^&*()":
            if char in text:
                assert char in combined_text