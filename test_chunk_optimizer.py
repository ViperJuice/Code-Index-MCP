"""
Unit tests for chunk optimization functionality.

Tests the chunk optimizer including:
- Different chunking strategies (fixed, sentence, paragraph, semantic, hybrid)
- Token estimation
- Sentence and paragraph splitting
- Semantic boundary detection
- Chunk size balancing
- Overlap handling
- Edge cases and error handling
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import uuid

from mcp_server.document_processing.chunk_optimizer import (
    ChunkOptimizer,
    ChunkingStrategy,
    ChunkingConfig,
    TokenEstimator,
    SentenceSplitter,
    ParagraphSplitter,
    SemanticAnalyzer,
    FixedSizeChunkingStrategy,
    SentenceBasedChunkingStrategy,
    ParagraphBasedChunkingStrategy,
    SemanticBasedChunkingStrategy,
    HybridChunkingStrategy,
    create_chunk_optimizer
)
from mcp_server.document_processing.document_interfaces import (
    DocumentChunk,
    ChunkType,
    ChunkMetadata,
    DocumentStructure,
    Section
)


class TestTokenEstimator:
    """Test token estimation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.estimator = TokenEstimator()
        
    def test_estimate_plain_text(self):
        """Test token estimation for plain text."""
        text = "This is a simple sentence with eight words."
        tokens = self.estimator.estimate_tokens(text)
        
        # Token estimation: len(text) * 0.75 = 44 * 0.75 = 33
        # Expecting around 30-35 tokens with the algorithm
        assert 30 <= tokens <= 35
        
    def test_estimate_code_content(self):
        """Test token estimation for code content."""
        code = """
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total
"""
        tokens = self.estimator.estimate_tokens(code)
        
        # Code typically has more tokens due to syntax
        base_estimate = len(code) * 0.75
        assert tokens > base_estimate  # Should have boost for code
        
    def test_estimate_punctuation_heavy(self):
        """Test token estimation for punctuation-heavy text."""
        text = "array[0].method().property; obj->ptr->val = func(a, b, c);"
        tokens = self.estimator.estimate_tokens(text)
        
        # Punctuation-heavy text gets a boost
        base_estimate = len(text) * 0.75
        assert tokens > base_estimate
        
    def test_estimate_empty_text(self):
        """Test token estimation for empty text."""
        assert self.estimator.estimate_tokens("") == 0
        assert self.estimator.estimate_tokens("   ") == 0


class TestSentenceSplitter:
    """Test sentence splitting functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.splitter = SentenceSplitter()
        
    def test_split_standard_sentences(self):
        """Test splitting standard sentences."""
        text = "First sentence. Second sentence! Third sentence? Fourth."
        sentences = self.splitter.split_sentences(text)
        
        assert len(sentences) == 4
        assert sentences[0] == "First sentence."
        assert sentences[1] == "Second sentence!"
        assert sentences[2] == "Third sentence?"
        assert sentences[3] == "Fourth."
        
    def test_split_with_newlines(self):
        """Test splitting with newlines."""
        text = """First paragraph sentence.
        
Another paragraph here.

Yet another sentence."""
        
        sentences = self.splitter.split_sentences(text)
        assert len(sentences) == 3
        
    def test_preserve_code_blocks(self):
        """Test that code blocks are preserved."""
        text = """Here's an example:

```python
def hello():
    print("Hello, World!")
```

And another sentence."""
        
        sentences = self.splitter.split_sentences(text)
        
        # Code block should be preserved as one unit
        code_sentence = next((s for s in sentences if 'def hello()' in s), None)
        assert code_sentence is not None
        assert 'print("Hello, World!")' in code_sentence
        
    def test_handle_list_items(self):
        """Test detection of list items."""
        text = """Regular sentence.

- First list item
- Second list item

1. Numbered item
2. Another numbered item"""
        
        sentences = self.splitter.split_sentences(text)
        
        # Check list item detection
        assert self.splitter.is_list_item("- First list item")
        assert self.splitter.is_list_item("1. Numbered item")
        assert not self.splitter.is_list_item("Regular sentence.")


class TestParagraphSplitter:
    """Test paragraph splitting functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.splitter = ParagraphSplitter()
        self.estimator = TokenEstimator()
        
    def test_split_paragraphs(self):
        """Test basic paragraph splitting."""
        text = """First paragraph here.
Still first paragraph.

Second paragraph starts here.
Continues on this line.

Third paragraph is separate."""
        
        paragraphs = self.splitter.split_paragraphs(text)
        
        assert len(paragraphs) == 3
        assert "First paragraph" in paragraphs[0]
        assert "Still first paragraph" in paragraphs[0]
        assert "Second paragraph" in paragraphs[1]
        
    def test_merge_short_paragraphs(self):
        """Test merging of short paragraphs."""
        paragraphs = [
            "Short.",
            "Also short.",
            "This is a longer paragraph with more content that exceeds the minimum size.",
            "Tiny.",
            "Another reasonable paragraph with sufficient content."
        ]
        
        merged = self.splitter.merge_short_paragraphs(paragraphs, 50, self.estimator)
        
        # Short paragraphs should be merged
        assert len(merged) < len(paragraphs)
        assert any("Short." in p and "Also short." in p for p in merged)
        
    def test_handle_empty_input(self):
        """Test handling of empty input."""
        assert self.splitter.split_paragraphs("") == []
        assert self.splitter.split_paragraphs("   \n\n   ") == []
        assert self.splitter.merge_short_paragraphs([], 50, self.estimator) == []


class TestSemanticAnalyzer:
    """Test semantic analysis functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = SemanticAnalyzer()
        
    def test_find_topic_boundaries(self):
        """Test finding topic boundaries."""
        text = """Introduction to the topic.

However, there's another perspective to consider.

## New Section

Furthermore, we should note that this is important.

In conclusion, we have covered several points."""
        
        boundaries = self.analyzer.find_topic_boundaries(text)
        
        assert len(boundaries) > 0
        # Should find boundaries at transition words and headings
        assert any(pos < len(text) for pos in boundaries)
        
    def test_calculate_coherence_score(self):
        """Test coherence score calculation."""
        text1 = "Machine learning models require training data."
        text2 = "Training data is essential for machine learning algorithms."
        text3 = "The weather today is sunny and warm."
        
        # High coherence between related texts
        score1 = self.analyzer.calculate_coherence_score(text1, text2)
        assert score1 > 0.3
        
        # Low coherence between unrelated texts
        score2 = self.analyzer.calculate_coherence_score(text1, text3)
        assert score2 < 0.2
        
        # Perfect coherence with self
        score3 = self.analyzer.calculate_coherence_score(text1, text1)
        assert score3 == 1.0
        
    def test_handle_empty_text(self):
        """Test handling of empty text."""
        assert self.analyzer.calculate_coherence_score("", "text") == 0.0
        assert self.analyzer.calculate_coherence_score("text", "") == 0.0
        assert self.analyzer.find_topic_boundaries("") == []


class TestChunkOptimizer:
    """Test the main chunk optimizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ChunkingConfig(
            strategy=ChunkingStrategy.HYBRID,
            max_chunk_size=100,
            min_chunk_size=20,
            overlap_size=10
        )
        self.optimizer = ChunkOptimizer(self.config)
        
    def test_calculate_optimal_chunk_size(self):
        """Test optimal chunk size calculation."""
        # Short content
        short_content = "This is short content."
        size = self.optimizer.calculate_optimal_chunk_size(short_content)
        assert size <= len(short_content)
        
        # Long content
        long_content = "This is much longer content. " * 100
        size = self.optimizer.calculate_optimal_chunk_size(long_content)
        assert size == self.config.max_chunk_size
        
        # With structure
        structure = Mock(spec=DocumentStructure)
        structure.sections = [Mock() for _ in range(5)]
        size_with_structure = self.optimizer.calculate_optimal_chunk_size(
            long_content, structure
        )
        assert size_with_structure > 0
        
    def test_find_optimal_split_points(self):
        """Test finding optimal split points."""
        text = """First sentence. Second sentence. Third sentence.

New paragraph starts here. It continues with more content.

Another paragraph with different content."""
        
        target_size = 50
        split_points = self.optimizer.find_optimal_split_points(text, target_size)
        
        assert len(split_points) > 0
        assert all(0 < point < len(text) for point in split_points)
        # Should prefer paragraph boundaries (check if split is at or near newlines)
        assert any(
            '\n' in text[max(0, point-1):min(len(text), point+1)]
            for point in split_points
        )
        
    def test_balance_chunk_sizes(self):
        """Test chunk size balancing."""
        chunks = [
            "Very short.",  # Too small
            "This is a medium-sized chunk with appropriate content.",
            "Tiny.",  # Too small
            "Another good chunk with sufficient content here.",
            "This is an extremely long chunk " * 20  # Too large
        ]
        
        balanced = self.optimizer.balance_chunk_sizes(chunks, 20, 100)
        
        # Should merge small chunks and split large ones
        assert len(balanced) != len(chunks)
        # No chunk should be too small (except possibly the last one)
        for chunk in balanced[:-1]:
            assert self.optimizer.token_estimator.estimate_tokens(chunk) >= 20
            
    def test_maintain_semantic_coherence(self):
        """Test semantic coherence maintenance."""
        chunks = [
            "Introduction to machine learning concepts.",
            "However, deep learning is different. Neural networks use layers.",
            "The weather is sunny today. Birds are singing.",  # Unrelated
            "Returning to neural networks, backpropagation is key."
        ]
        
        coherent = self.optimizer.maintain_semantic_coherence(chunks)
        
        assert len(coherent) == len(chunks)
        # The optimizer might adjust boundaries to improve coherence


class TestChunkingStrategies:
    """Test different chunking strategies."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ChunkingConfig(max_chunk_size=50, min_chunk_size=10, overlap_size=10)
        self.optimizer = ChunkOptimizer(self.config)
        self.structure = DocumentStructure(
            title="Test Document",
            sections=[],
            metadata={"path": "test.txt"}
        )
        
    def test_fixed_size_strategy(self):
        """Test fixed-size chunking strategy."""
        strategy = FixedSizeChunkingStrategy(self.optimizer)
        content = "This is test content. " * 20
        
        chunks = strategy.chunk(content, self.structure)
        
        assert len(chunks) > 1
        assert all(isinstance(c, DocumentChunk) for c in chunks)
        # Check overlap
        if len(chunks) > 1:
            # There should be some overlap between consecutive chunks
            assert any(
                chunks[i].content[-5:] in chunks[i+1].content[:20]
                for i in range(len(chunks)-1)
            )
            
    def test_sentence_based_strategy(self):
        """Test sentence-based chunking strategy."""
        strategy = SentenceBasedChunkingStrategy(self.optimizer)
        content = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence."
        
        chunks = strategy.chunk(content, self.structure)
        
        assert len(chunks) >= 1
        # Each chunk should end with sentence boundary
        for chunk in chunks:
            assert chunk.content.rstrip().endswith(('.', '!', '?'))
            
    def test_paragraph_based_strategy(self):
        """Test paragraph-based chunking strategy."""
        strategy = ParagraphBasedChunkingStrategy(self.optimizer)
        content = """First paragraph here.

Second paragraph with more content.

Third paragraph is the longest with much more content to ensure it exceeds minimum size.

Fourth paragraph."""
        
        chunks = strategy.chunk(content, self.structure)
        
        assert len(chunks) >= 1
        # Each chunk should be a complete paragraph or merged paragraphs
        for chunk in chunks:
            assert chunk.content.strip() != ""
            
    def test_semantic_based_strategy(self):
        """Test semantic-based chunking strategy."""
        strategy = SemanticBasedChunkingStrategy(self.optimizer)
        content = """# Introduction

This is the introduction.

## Main Content

However, the main content starts here.

## Conclusion

In conclusion, we summarize."""
        
        chunks = strategy.chunk(content, self.structure)
        
        assert len(chunks) >= 1
        # Should respect semantic boundaries
        intro_chunk = next((c for c in chunks if "introduction" in c.content.lower()), None)
        assert intro_chunk is not None
        
    def test_hybrid_strategy(self):
        """Test hybrid chunking strategy."""
        strategy = HybridChunkingStrategy(self.optimizer)
        
        # Create structure with sections
        section1 = Section(
            id="1",
            heading="Introduction",
            level=1,
            content="This is the introduction section."
        )
        section2 = Section(
            id="2",
            heading="Main Content",
            level=1,
            content="This is the main content section with more text."
        )
        self.structure.sections = [section1, section2]
        self.structure.outline = section1
        section1.children = [section2]
        
        content = """# Introduction

This is the introduction section.

# Main Content  

This is the main content section with more text."""
        
        chunks = strategy.chunk(content, self.structure)
        
        assert len(chunks) >= 1
        assert all(isinstance(c, DocumentChunk) for c in chunks)
        # Should maintain section hierarchy in metadata
        assert any(c.metadata.section_hierarchy for c in chunks)
        
    def test_strategy_validation(self):
        """Test chunk validation across strategies."""
        strategies = [
            FixedSizeChunkingStrategy(self.optimizer),
            SentenceBasedChunkingStrategy(self.optimizer),
            ParagraphBasedChunkingStrategy(self.optimizer),
            SemanticBasedChunkingStrategy(self.optimizer),
            HybridChunkingStrategy(self.optimizer)
        ]
        
        # Create a valid chunk
        valid_chunk = DocumentChunk(
            id="test",
            content="This is valid content with enough words.",  # Shorter to fit in 50 tokens
            type=ChunkType.PARAGRAPH,
            metadata=ChunkMetadata(
                document_path="test.txt",
                section_hierarchy=[],
                chunk_index=0,
                total_chunks=1,
                has_code=False,
                word_count=8,
                line_start=0,
                line_end=0
            )
        )
        
        # All strategies should validate this chunk
        for strategy in strategies:
            assert strategy.validate_chunk(valid_chunk)
            
        # Create an invalid (too small) chunk
        small_chunk = DocumentChunk(
            id="small",
            content="Tiny",
            type=ChunkType.PARAGRAPH,
            metadata=ChunkMetadata(
                document_path="test.txt",
                section_hierarchy=[],
                chunk_index=0,
                total_chunks=1,
                has_code=False
            )
        )
        
        # Most strategies should reject this
        for strategy in strategies:
            if not isinstance(strategy, SemanticBasedChunkingStrategy):
                assert not strategy.validate_chunk(small_chunk)


class TestChunkOptimizerFactory:
    """Test chunk optimizer factory function."""
    
    def test_create_optimizer_with_strategies(self):
        """Test creating optimizer with different strategies."""
        strategies = [
            ChunkingStrategy.FIXED_SIZE,
            ChunkingStrategy.SENTENCE_BASED,
            ChunkingStrategy.PARAGRAPH_BASED,
            ChunkingStrategy.SEMANTIC_BASED,
            ChunkingStrategy.HYBRID
        ]
        
        for strategy in strategies:
            optimizer, strategy_instance = create_chunk_optimizer(strategy)
            
            assert isinstance(optimizer, ChunkOptimizer)
            assert optimizer.config.strategy == strategy
            
            # Verify correct strategy instance
            if strategy == ChunkingStrategy.FIXED_SIZE:
                assert isinstance(strategy_instance, FixedSizeChunkingStrategy)
            elif strategy == ChunkingStrategy.SENTENCE_BASED:
                assert isinstance(strategy_instance, SentenceBasedChunkingStrategy)
            elif strategy == ChunkingStrategy.PARAGRAPH_BASED:
                assert isinstance(strategy_instance, ParagraphBasedChunkingStrategy)
            elif strategy == ChunkingStrategy.SEMANTIC_BASED:
                assert isinstance(strategy_instance, SemanticBasedChunkingStrategy)
            elif strategy == ChunkingStrategy.HYBRID:
                assert isinstance(strategy_instance, HybridChunkingStrategy)
                
    def test_create_optimizer_with_custom_config(self):
        """Test creating optimizer with custom configuration."""
        custom_config = ChunkingConfig(
            strategy=ChunkingStrategy.SENTENCE_BASED,
            max_chunk_size=200,
            min_chunk_size=50,
            overlap_size=20,
            semantic_threshold=0.8
        )
        
        optimizer, strategy = create_chunk_optimizer(
            ChunkingStrategy.SENTENCE_BASED,
            custom_config
        )
        
        assert optimizer.config.max_chunk_size == 200
        assert optimizer.config.min_chunk_size == 50
        assert optimizer.config.overlap_size == 20
        assert optimizer.config.semantic_threshold == 0.8


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = ChunkOptimizer()
        self.structure = DocumentStructure(
            title="Test",
            sections=[],
            metadata={}
        )
        
    def test_empty_content(self):
        """Test handling of empty content."""
        strategies = [
            FixedSizeChunkingStrategy(self.optimizer),
            SentenceBasedChunkingStrategy(self.optimizer),
            ParagraphBasedChunkingStrategy(self.optimizer),
            SemanticBasedChunkingStrategy(self.optimizer),
            HybridChunkingStrategy(self.optimizer)
        ]
        
        for strategy in strategies:
            chunks = strategy.chunk("", self.structure)
            assert len(chunks) == 0 or (len(chunks) == 1 and chunks[0].content == "")
            
    def test_single_word_content(self):
        """Test handling of single word content."""
        strategy = HybridChunkingStrategy(self.optimizer)
        chunks = strategy.chunk("Hello", self.structure)
        
        assert len(chunks) == 1
        assert chunks[0].content == "Hello"
        
    def test_very_long_word(self):
        """Test handling of very long words."""
        long_word = "a" * 1000
        strategy = FixedSizeChunkingStrategy(self.optimizer)
        chunks = strategy.chunk(long_word, self.structure)
        
        assert len(chunks) >= 1
        # Should handle without error
        
    def test_unicode_content(self):
        """Test handling of Unicode content."""
        unicode_content = "Hello 你好 مرحبا שלום 🌍🚀"
        strategy = HybridChunkingStrategy(self.optimizer)
        chunks = strategy.chunk(unicode_content, self.structure)
        
        assert len(chunks) >= 1
        assert "你好" in chunks[0].content
        assert "🌍" in chunks[0].content
        
    def test_malformed_structure(self):
        """Test handling of malformed document structure."""
        # Structure with circular reference
        section = Section(
            id="1",
            heading="Circular",
            level=1,
            content="Content"
        )
        section.parent = section  # Circular reference
        
        bad_structure = DocumentStructure(
            title="Bad",
            sections=[section],
            metadata={}
        )
        
        strategy = HybridChunkingStrategy(self.optimizer)
        # Should handle without infinite loop
        chunks = strategy.chunk("Content", bad_structure)
        assert len(chunks) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])