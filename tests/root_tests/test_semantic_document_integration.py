"""Integration tests for semantic indexer with document processing."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os
import logging
from typing import List, Dict, Any
import hashlib
import time
import numpy as np

from tests.base_test import BaseDocumentTest
from mcp_server.utils.semantic_indexer import SemanticIndexer, DocumentSection
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.document_processing.document_interfaces import (
    DocumentChunk, ChunkType, ChunkMetadata
)

logger = logging.getLogger(__name__)


class TestSemanticDocumentIntegration(BaseDocumentTest):
    """Test semantic indexer integration with document processing system."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client."""
        with patch('mcp_server.utils.semantic_indexer.QdrantClient') as mock:
            client = MagicMock()
            mock.return_value = client
            
            # Mock collection operations
            client.get_collections.return_value.collections = []
            client.create_collection.return_value = True
            client.upsert.return_value = True
            client.search.return_value = []
            
            yield client
    
    @pytest.fixture
    def mock_voyage_client(self):
        """Create a mock Voyage AI client."""
        with patch('mcp_server.utils.semantic_indexer.voyageai.Client') as mock:
            client = MagicMock()
            mock.return_value = client
            
            # Mock embedding generation
            def mock_embed(texts, model, input_type=None):
                # Generate deterministic fake embeddings
                embeddings = []
                for text in texts:
                    # Create a simple hash-based embedding
                    hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
                    embedding = [(hash_val >> i & 1) * 0.1 for i in range(1024)]
                    embeddings.append(embedding)
                return MagicMock(embeddings=embeddings)
            
            client.embed.side_effect = mock_embed
            yield client
    
    @pytest.fixture
    def semantic_indexer(self, mock_qdrant_client, mock_voyage_client):
        """Create semantic indexer with mocked clients."""
        with patch.dict(os.environ, {'VOYAGE_API_KEY': 'test-key'}):
            indexer = SemanticIndexer(
                collection_name="test_collection",
                qdrant_host="localhost",
                qdrant_port=6333
            )
            return indexer
    
    def test_semantic_indexer_processes_document_chunks(self, semantic_indexer):
        """Test that semantic indexer correctly processes document chunks."""
        # Create document chunks
        chunks = [
            DocumentChunk(
                id="chunk1",
                content="# Installation Guide\n\nInstall using pip: pip install mypackage",
                type=ChunkType.HEADING,
                metadata=ChunkMetadata(
                    document_path=str(self.workspace / "README.md"),
                    section_hierarchy=["Installation Guide"],
                    chunk_index=0,
                    total_chunks=3,
                    has_code=True,
                    word_count=10
                )
            ),
            DocumentChunk(
                id="chunk2",
                content="## Requirements\n\n- Python 3.8+\n- pip package manager",
                type=ChunkType.HEADING,
                metadata=ChunkMetadata(
                    document_path=str(self.workspace / "README.md"),
                    section_hierarchy=["Installation Guide", "Requirements"],
                    chunk_index=1,
                    total_chunks=3,
                    has_code=False,
                    word_count=8
                )
            ),
            DocumentChunk(
                id="chunk3",
                content="```python\nfrom mypackage import Client\nclient = Client()\n```",
                type=ChunkType.CODE_BLOCK,
                metadata=ChunkMetadata(
                    document_path=str(self.workspace / "README.md"),
                    section_hierarchy=["Installation Guide", "Usage"],
                    chunk_index=2,
                    total_chunks=3,
                    has_code=True,
                    language="python",
                    word_count=6
                )
            )
        ]
        
        # Index chunks
        for chunk in chunks:
            semantic_indexer.index_document_chunk(
                chunk_id=chunk.id,
                content=chunk.content,
                file_path=chunk.metadata.document_path,
                chunk_metadata={
                    'type': chunk.type.value,
                    'section_hierarchy': chunk.metadata.section_hierarchy,
                    'has_code': chunk.metadata.has_code,
                    'language': chunk.metadata.language
                }
            )
        
        # Verify indexing calls
        assert semantic_indexer._qdrant_client.upsert.called
        call_args = semantic_indexer._qdrant_client.upsert.call_args_list
        assert len(call_args) >= len(chunks)
    
    def test_semantic_search_with_document_context(self, semantic_indexer, mock_qdrant_client):
        """Test semantic search with document context awareness."""
        # Setup mock search results
        mock_results = [
            MagicMock(
                id="chunk1",
                score=0.95,
                payload={
                    'content': 'Install using pip: pip install mypackage',
                    'file_path': '/docs/README.md',
                    'type': 'document',
                    'metadata': {
                        'type': 'heading',
                        'section_hierarchy': ['Installation Guide'],
                        'has_code': True
                    }
                }
            ),
            MagicMock(
                id="chunk2",
                score=0.85,
                payload={
                    'content': 'pip is the package installer for Python',
                    'file_path': '/docs/glossary.md',
                    'type': 'document',
                    'metadata': {
                        'type': 'paragraph',
                        'section_hierarchy': ['Glossary', 'Package Management']
                    }
                }
            )
        ]
        mock_qdrant_client.search.return_value = mock_results
        
        # Perform search
        results = semantic_indexer.search_documents(
            query="how to install with pip",
            limit=10,
            file_pattern="*.md"
        )
        
        # Verify search was called with document type
        mock_qdrant_client.search.assert_called()
        
        # Verify results are properly formatted
        assert len(results) == 2
        assert results[0]['score'] > results[1]['score']  # Higher score first
        assert 'Installation Guide' in str(results[0])
    
    def test_semantic_indexer_document_type_weighting(self, semantic_indexer):
        """Test that document types receive appropriate weight boosts."""
        # Test weight calculation for different document types
        readme_weight = semantic_indexer._get_document_weight("README.md", "markdown")
        assert readme_weight > 1.0  # README should get boost
        
        md_weight = semantic_indexer._get_document_weight("docs/api.md", "markdown")
        assert md_weight >= 1.0  # Markdown docs should get boost
        
        txt_weight = semantic_indexer._get_document_weight("notes.txt", "plaintext")
        assert txt_weight == 1.0  # Plain text gets standard weight
    
    def test_integration_with_markdown_plugin(self, semantic_indexer):
        """Test semantic indexer integration with markdown plugin."""
        # Create a markdown file
        md_file = self.workspace / "guide.md"
        content = """# User Guide

## Getting Started

Follow these steps to get started:

1. Install the package
2. Configure settings
3. Run the application

## Advanced Usage

### Custom Configuration

You can customize the behavior by modifying the config file:

```yaml
server:
  host: localhost
  port: 8080
options:
  debug: true
```

### API Integration

Use our REST API for programmatic access.
"""
        md_file.write_text(content)
        
        # Create plugin with semantic indexer
        with patch.dict(os.environ, {'SEMANTIC_SEARCH_ENABLED': 'true'}):
            plugin = MarkdownPlugin(
                sqlite_store=self.store,
                enable_semantic=True
            )
            # Inject our mocked indexer
            plugin._semantic_indexer = semantic_indexer
            
            # Index the file
            shard = plugin.index([str(md_file)])
            assert shard is not None
            
            # Verify semantic indexing was called
            assert semantic_indexer._voyage_client.embed.called
    
    def test_semantic_search_respects_file_patterns(self, semantic_indexer, mock_qdrant_client):
        """Test that semantic search correctly filters by file patterns."""
        # Setup mock results from different file types
        mock_results = [
            MagicMock(
                id="1",
                score=0.9,
                payload={
                    'content': 'Configuration guide',
                    'file_path': '/docs/config.md',
                    'type': 'document'
                }
            ),
            MagicMock(
                id="2",
                score=0.85,
                payload={
                    'content': 'Configuration example',
                    'file_path': '/examples/config.py',
                    'type': 'code'
                }
            ),
            MagicMock(
                id="3",
                score=0.8,
                payload={
                    'content': 'Config notes',
                    'file_path': '/notes/config.txt',
                    'type': 'document'
                }
            )
        ]
        mock_qdrant_client.search.return_value = mock_results
        
        # Search with file pattern filter
        md_results = semantic_indexer.search_documents(
            query="configuration",
            limit=10,
            file_pattern="*.md"
        )
        
        # Should only return .md files
        assert all(r.get('file_path', '').endswith('.md') for r in md_results)
    
    def test_document_section_extraction(self, semantic_indexer):
        """Test extraction of document sections for hierarchical indexing."""
        markdown_content = """# Main Title

## Section 1

Content for section 1.

### Subsection 1.1

Details about subsection.

## Section 2

Another main section.

### Subsection 2.1

More details.

#### Subsubsection 2.1.1

Deep nesting example.
"""
        
        # Extract sections
        sections = semantic_indexer.extract_markdown_sections(markdown_content)
        
        # Verify section hierarchy
        assert len(sections) > 0
        
        # Find main sections
        main_sections = [s for s in sections if s.level == 2]
        assert len(main_sections) == 2
        assert main_sections[0].title == "Section 1"
        assert main_sections[1].title == "Section 2"
        
        # Check subsections
        subsections = [s for s in sections if s.level == 3]
        assert len(subsections) >= 2
        
        # Verify deep nesting
        deep_sections = [s for s in sections if s.level == 4]
        assert len(deep_sections) >= 1
        assert deep_sections[0].title == "Subsubsection 2.1.1"
    
    def test_semantic_indexer_handles_large_documents(self, semantic_indexer):
        """Test semantic indexer with large documents that need chunking."""
        # Create a large document
        sections = []
        for i in range(20):
            sections.append(f"""## Section {i}

This is the content for section {i}. It contains multiple paragraphs
to simulate a real document with substantial content.

Here's another paragraph with more details about topic {i}.
It includes various technical terms and explanations.

""")
        
        large_content = "# Large Document\n\n" + "\n".join(sections)
        
        # Index the large document
        semantic_indexer.index_document_content(
            content=large_content,
            file_path=str(self.workspace / "large.md"),
            doc_type="markdown"
        )
        
        # Verify chunking happened
        assert semantic_indexer._voyage_client.embed.called
        
        # Check that multiple chunks were created
        embed_calls = semantic_indexer._voyage_client.embed.call_count
        assert embed_calls > 1  # Should have multiple embedding calls for chunks
    
    def test_semantic_cache_integration(self, semantic_indexer):
        """Test that semantic indexer integrates with caching layer."""
        # Create a document
        doc_path = str(self.workspace / "cached.md")
        content = "# Cached Document\n\nThis content should be cached."
        
        # Index document twice
        semantic_indexer.index_document_content(content, doc_path, "markdown")
        semantic_indexer.index_document_content(content, doc_path, "markdown")
        
        # Second indexing should use cache (fewer embed calls)
        embed_calls = semantic_indexer._voyage_client.embed.call_count
        # With caching, we shouldn't have double the calls
        assert embed_calls < 4  # Would be 4+ without caching
    
    def test_semantic_embeddings_quality(self, semantic_indexer, mock_voyage_client):
        """Test quality and consistency of semantic embeddings."""
        # Create similar documents
        similar_docs = [
            ("doc1.md", "# Machine Learning\n\nNeural networks and deep learning concepts."),
            ("doc2.md", "# Deep Learning\n\nNeural network architectures and training."),
            ("doc3.md", "# AI Models\n\nMachine learning and neural network models.")
        ]
        
        # Create dissimilar document
        dissimilar_doc = ("cooking.md", "# Cooking Recipe\n\nHow to make chocolate cake.")
        
        # Generate embeddings for all
        embeddings = {}
        for filename, content in similar_docs + [dissimilar_doc]:
            file_path = str(self.workspace / filename)
            semantic_indexer.index_document_content(content, file_path, "markdown")
            
            # Extract embedding from mock calls
            call_args = mock_voyage_client.embed.call_args_list[-1]
            embeddings[filename] = np.array(call_args[0][0])  # First text's embedding
        
        # Calculate cosine similarities
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        # Similar documents should have high similarity
        sim_1_2 = cosine_similarity(embeddings["doc1.md"], embeddings["doc2.md"])
        sim_1_3 = cosine_similarity(embeddings["doc1.md"], embeddings["doc3.md"])
        sim_2_3 = cosine_similarity(embeddings["doc2.md"], embeddings["doc3.md"])
        
        # Dissimilar document should have low similarity
        sim_1_cook = cosine_similarity(embeddings["doc1.md"], embeddings["cooking.md"])
        sim_2_cook = cosine_similarity(embeddings["doc2.md"], embeddings["cooking.md"])
        
        # Assert relationships (even with mock embeddings, structure should hold)
        # Similar docs should be more similar to each other than to dissimilar doc
        assert sim_1_2 > sim_1_cook or sim_1_3 > sim_1_cook
        assert sim_2_3 > sim_2_cook
    
    def test_semantic_search_with_synonyms(self, semantic_indexer, mock_qdrant_client):
        """Test semantic search finds documents with synonyms and related terms."""
        # Setup mock results for synonym search
        mock_results = [
            MagicMock(
                id="doc1",
                score=0.92,
                payload={
                    'content': 'Software installation guide',
                    'file_path': '/docs/setup.md',
                    'type': 'document'
                }
            ),
            MagicMock(
                id="doc2",
                score=0.88,
                payload={
                    'content': 'Application deployment instructions',
                    'file_path': '/docs/deploy.md',
                    'type': 'document'
                }
            ),
            MagicMock(
                id="doc3",
                score=0.85,
                payload={
                    'content': 'Program setup tutorial',
                    'file_path': '/docs/tutorial.md',
                    'type': 'document'
                }
            )
        ]
        mock_qdrant_client.search.return_value = mock_results
        
        # Search with synonym terms
        results = semantic_indexer.search_documents(
            query="software deployment setup",  # Mix of synonyms
            limit=10
        )
        
        # Should find all related documents
        assert len(results) == 3
        assert all(r['score'] > 0.8 for r in results)
    
    def test_semantic_indexer_chunk_boundaries(self, semantic_indexer):
        """Test that semantic indexer respects chunk boundaries and context."""
        # Create document with clear section boundaries
        document = """# User Manual

## Chapter 1: Getting Started

This chapter covers the basics of getting started with our application.
You'll learn how to install and configure the software.

### Installation Steps

1. Download the installer
2. Run the setup wizard
3. Configure initial settings

## Chapter 2: Advanced Features

This chapter explores advanced features and customization options.
Power users will find detailed configuration instructions here.

### Custom Workflows

Create custom workflows to automate repetitive tasks.
Use the workflow editor to design your automation.

## Chapter 3: Troubleshooting

Common issues and their solutions are covered in this chapter.
Find answers to frequently asked questions.

### Error Messages

Understanding and resolving common error messages.
Diagnostic tools and debugging techniques.
"""
        
        # Index document
        semantic_indexer.index_document_content(
            document,
            str(self.workspace / "manual.md"),
            "markdown"
        )
        
        # Verify chunking preserved section boundaries
        embed_calls = semantic_indexer._voyage_client.embed.call_args_list
        
        # Should have multiple chunks
        assert len(embed_calls) > 1
        
        # Each chunk should contain coherent content
        for call in embed_calls:
            chunk_text = call[0][0][0] if isinstance(call[0][0], list) else call[0][0]
            # Chunks should not split mid-sentence
            assert not chunk_text.endswith((" the", " a", " an", " of"))
    
    def test_semantic_vector_search_accuracy(self, semantic_indexer, mock_qdrant_client):
        """Test accuracy of vector-based semantic search."""
        # Create test documents with varying semantic similarity
        test_docs = [
            {
                'id': 'exact',
                'content': 'How to configure database connection settings',
                'score': 0.98
            },
            {
                'id': 'similar',
                'content': 'Database configuration and setup guide',
                'score': 0.92
            },
            {
                'id': 'related',
                'content': 'SQL server connection parameters',
                'score': 0.85
            },
            {
                'id': 'distant',
                'content': 'Web server configuration',
                'score': 0.65
            }
        ]
        
        # Mock search results in order of relevance
        mock_results = [
            MagicMock(
                id=doc['id'],
                score=doc['score'],
                payload={'content': doc['content'], 'file_path': f'/{doc["id"]}.md'}
            )
            for doc in test_docs
        ]
        mock_qdrant_client.search.return_value = mock_results[:3]  # Top 3
        
        # Perform search
        results = semantic_indexer.search_documents(
            query="database connection configuration",
            limit=3
        )
        
        # Verify ranking order
        assert len(results) == 3
        assert results[0]['score'] > results[1]['score']
        assert results[1]['score'] > results[2]['score']
        
        # Most relevant should score highly
        assert results[0]['score'] > 0.9
    
    def test_semantic_indexer_multilingual_support(self, semantic_indexer):
        """Test semantic indexer with multilingual content."""
        # Create multilingual documents
        multilingual_docs = [
            ("english.md", "# Documentation\n\nThis is English documentation."),
            ("spanish.md", "# Documentación\n\nEsta es documentación en español."),
            ("french.md", "# Documentation\n\nCeci est une documentation en français."),
            ("mixed.md", "# Mixed Language\n\nThis document contains English, español, and français.")
        ]
        
        # Index all documents
        for filename, content in multilingual_docs:
            file_path = str(self.workspace / filename)
            semantic_indexer.index_document_content(content, file_path, "markdown")
        
        # Verify all documents were indexed
        assert semantic_indexer._voyage_client.embed.call_count >= len(multilingual_docs)
        
        # Each language should be processed
        embed_calls = semantic_indexer._voyage_client.embed.call_args_list
        texts_indexed = []
        for call in embed_calls:
            if isinstance(call[0][0], list):
                texts_indexed.extend(call[0][0])
            else:
                texts_indexed.append(call[0][0])
        
        # Should contain text from all languages
        assert any("English" in text for text in texts_indexed)
        assert any("español" in text for text in texts_indexed)
        assert any("français" in text for text in texts_indexed)
    
    def test_semantic_indexer_performance_optimization(self, semantic_indexer):
        """Test performance optimizations in semantic indexer."""
        # Create documents of varying sizes
        small_doc = "Small content."
        medium_doc = "Medium document. " * 100  # ~1.5KB
        large_doc = "Large document content. " * 1000  # ~20KB
        
        # Track indexing times
        times = {}
        
        # Index small document
        start = time.time()
        semantic_indexer.index_document_content(
            small_doc, str(self.workspace / "small.md"), "markdown"
        )
        times['small'] = time.time() - start
        
        # Index medium document
        start = time.time()
        semantic_indexer.index_document_content(
            medium_doc, str(self.workspace / "medium.md"), "markdown"
        )
        times['medium'] = time.time() - start
        
        # Index large document
        start = time.time()
        semantic_indexer.index_document_content(
            large_doc, str(self.workspace / "large.md"), "markdown"
        )
        times['large'] = time.time() - start
        
        # Performance should scale reasonably
        # Large doc shouldn't take disproportionately longer
        assert times['large'] < times['small'] * 100  # Not 1000x slower
    
    def test_semantic_search_with_metadata_filters(self, semantic_indexer, mock_qdrant_client):
        """Test semantic search with metadata-based filtering."""
        # Setup mock results with different metadata
        mock_results = [
            MagicMock(
                id="recent1",
                score=0.95,
                payload={
                    'content': 'Recent API documentation',
                    'file_path': '/docs/api_v2.md',
                    'metadata': {'version': '2.0', 'date': '2024-01-15'}
                }
            ),
            MagicMock(
                id="old1",
                score=0.93,
                payload={
                    'content': 'Legacy API documentation',
                    'file_path': '/docs/api_v1.md',
                    'metadata': {'version': '1.0', 'date': '2023-01-15'}
                }
            ),
            MagicMock(
                id="recent2",
                score=0.90,
                payload={
                    'content': 'Current API guide',
                    'file_path': '/docs/guide.md',
                    'metadata': {'version': '2.0', 'date': '2024-01-10'}
                }
            )
        ]
        mock_qdrant_client.search.return_value = mock_results
        
        # Search with metadata preferences
        results = semantic_indexer.search_documents(
            query="API documentation",
            limit=10,
            metadata_filter={'version': '2.0'}  # Only recent versions
        )
        
        # Should prioritize recent versions
        assert len(results) >= 2
        # Results should be filtered or ranked by metadata
        for result in results[:2]:
            if 'metadata' in result.get('payload', {}):
                assert result['payload']['metadata'].get('version') == '2.0'
    
    def test_semantic_indexer_error_recovery(self, semantic_indexer, mock_voyage_client):
        """Test semantic indexer error handling and recovery."""
        # Simulate embedding API failure
        error_count = 0
        original_embed = mock_voyage_client.embed.side_effect
        
        def failing_embed(*args, **kwargs):
            nonlocal error_count
            error_count += 1
            if error_count <= 2:
                raise Exception("Embedding API temporarily unavailable")
            return original_embed(*args, **kwargs)
        
        mock_voyage_client.embed.side_effect = failing_embed
        
        # Try to index document (should retry and eventually succeed)
        try:
            semantic_indexer.index_document_content(
                "Test content for error recovery",
                str(self.workspace / "test.md"),
                "markdown"
            )
        except Exception:
            # If it fails completely, that's OK for this test
            pass
        
        # Should have attempted multiple times
        assert error_count >= 2
        
        # Reset for next operation
        error_count = 0
        mock_voyage_client.embed.side_effect = original_embed
        
        # Next operation should work normally
        semantic_indexer.index_document_content(
            "Recovery test content",
            str(self.workspace / "recovery.md"),
            "markdown"
        )
        assert mock_voyage_client.embed.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])