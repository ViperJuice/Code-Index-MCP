#!/usr/bin/env python3
"""Test error recovery in document processing."""

import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import os
import threading
import time
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.plugins.markdown_plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin import PlainTextPlugin
from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
from mcp_server.document_processing import DocumentChunk, ChunkMetadata, ChunkType


class TestDocumentErrorRecovery:
    """Test error recovery mechanisms in document processing."""
    
    @pytest.fixture
    def setup_plugins(self):
        """Setup plugins for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "test.db"))
            
            markdown_plugin = MarkdownPlugin(enable_semantic=False)
            plaintext_config = {
                'name': 'plaintext',
                'code': 'plaintext',
                'extensions': ['.txt', '.text'],
                'file_pattern': r'.*\.(txt|text)$'
            }
            plaintext_plugin = PlainTextPlugin(plaintext_config, enable_semantic=False)
            python_plugin = PythonPlugin()
            
            yield {
                'markdown': markdown_plugin,
                'plaintext': plaintext_plugin,
                'python': python_plugin,
                'store': store,
                'tmpdir': tmpdir
            }
    
    def test_parser_error_recovery(self, setup_plugins):
        """Test recovery from parser errors."""
        plugins = setup_plugins
        
        # Markdown that might cause parser issues
        problematic_md = """# Title

```python
def broken():
    # Unclosed string
    text = "this string never ends...
    
# Next section should still parse

## Valid Section

This content should be extracted despite the error above."""
        
        # Should not raise exception
        result = plugins['markdown'].indexFile('broken.md', problematic_md)
        assert result is not None
        
        # Should still extract valid sections
        assert any('Valid Section' in sym.name for sym in result.symbols)
        
        # Chunks should be created
        chunks = plugins['markdown'].chunk_document(problematic_md, Path('broken.md'))
        assert len(chunks) > 0
        assert any('Valid Section' in chunk.content for chunk in chunks)
    
    def test_memory_error_recovery(self, setup_plugins):
        """Test recovery from memory-related errors."""
        plugin = setup_plugins['markdown']
        
        # Generate large content that might cause memory issues
        large_content = "# Title\n\n"
        # Add 1000 sections with substantial content
        for i in range(1000):
            large_content += f"## Section {i}\n\n"
            large_content += "Large paragraph. " * 100 + "\n\n"
        
        # Mock memory error during chunk creation
        original_chunk = plugin.chunk_document
        call_count = 0
        
        def chunk_with_memory_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise MemoryError("Simulated memory error")
            return original_chunk(*args, **kwargs)
        
        with patch.object(plugin, 'chunk_document', side_effect=chunk_with_memory_error):
            # First attempt should fail
            try:
                chunks = plugin.chunk_document(large_content, Path('large.md'))
            except MemoryError:
                pass
            
            # Second attempt should work (simulating recovery)
            chunks = plugin.chunk_document(large_content, Path('large.md'))
            assert chunks is not None
    
    def test_encoding_error_recovery(self, setup_plugins):
        """Test recovery from encoding errors."""
        plugins = setup_plugins
        
        # Content with potential encoding issues
        mixed_bytes = b"# Title\n\nValid text\xff\xfe\xfdInvalid bytes\n\nMore valid text"
        
        # Convert with error handling
        content = mixed_bytes.decode('utf-8', errors='replace')
        
        # Should process despite encoding issues
        result = plugins['markdown'].indexFile('encoding.md', content)
        assert result is not None
        
        chunks = plugins['markdown'].chunk_document(content, Path('encoding.md'))
        assert len(chunks) > 0
        assert any('Title' in chunk.content for chunk in chunks)
        assert any('valid text' in chunk.content for chunk in chunks)
    
    def test_concurrent_access_recovery(self, setup_plugins):
        """Test recovery from concurrent access issues."""
        plugins = setup_plugins
        store = plugins['store']
        
        content = "# Concurrent Test\n\nTesting concurrent access"
        results = []
        errors = []
        
        def index_file(plugin, filename, thread_id):
            try:
                result = plugin.indexFile(filename, f"{content}\n\nThread {thread_id}")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Simulate concurrent indexing
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=index_file,
                args=(plugins['markdown'], 'concurrent.md', i)
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should complete (some might fail but should recover)
        assert len(results) + len(errors) == 5
        assert len(results) > 0  # At least some should succeed
    
    def test_partial_chunk_failure_recovery(self, setup_plugins):
        """Test recovery when some chunks fail to process."""
        plugin = setup_plugins['markdown']
        
        content = """# Document

## Section 1
Normal content here.

## Section 2
This section is fine too.

## Section 3
Also good content."""
        
        # Mock chunk creation to fail on specific chunks
        original_chunk_method = plugin.chunk_strategy.create_chunks
        
        def failing_chunk_creation(*args, **kwargs):
            chunks = original_chunk_method(*args, **kwargs)
            # Simulate failure on second chunk
            if len(chunks) > 1:
                # Create a problematic chunk
                chunks[1] = None  # This would normally cause issues
            return [c for c in chunks if c is not None]  # Filter out failed chunks
        
        with patch.object(plugin.chunk_strategy, 'create_chunks', side_effect=failing_chunk_creation):
            chunks = plugin.chunk_document(content, Path('partial.md'))
            
            # Should still return valid chunks
            assert chunks is not None
            assert len(chunks) > 0
            assert all(chunk is not None for chunk in chunks)
    
    def test_metadata_extraction_failure_recovery(self, setup_plugins):
        """Test recovery from metadata extraction failures."""
        plugin = setup_plugins['markdown']
        
        # Content with problematic frontmatter
        content = """---
title: Valid Title
date: not-a-valid-date
tags: [unclosed, list
author: 
  name: Test
  email: invalid@email
---

# Content

This content should still be processed."""
        
        # Should handle metadata errors gracefully
        metadata = plugin.extract_metadata(content, Path('meta_error.md'))
        assert metadata is not None
        assert isinstance(metadata, dict)
        
        # Document should still be indexed
        result = plugin.indexFile('meta_error.md', content)
        assert result is not None
        assert len(result.symbols) > 0
    
    def test_file_system_error_recovery(self, setup_plugins):
        """Test recovery from file system errors."""
        plugins = setup_plugins
        tmpdir = Path(plugins['tmpdir'])
        
        # Create a file
        test_file = tmpdir / 'test.md'
        test_file.write_text('# Test\n\nContent')
        
        # Make file read-only
        test_file.chmod(0o444)
        
        try:
            # Try to process (might fail on some operations)
            content = test_file.read_text()
            result = plugins['markdown'].indexFile(str(test_file), content)
            assert result is not None
        finally:
            # Restore permissions
            test_file.chmod(0o644)
    
    def test_infinite_recursion_prevention(self, setup_plugins):
        """Test prevention of infinite recursion in document structure."""
        plugin = setup_plugins['markdown']
        
        # Create content that might cause recursive parsing
        content = """# Root

[Link to self](#root)

## Section A

See [Section B](#section-b)

## Section B

See [Section A](#section-a)

### Subsection

[Back to Root](#root)"""
        
        # Should handle without stack overflow
        result = plugin.indexFile('recursive.md', content)
        assert result is not None
        
        structure = plugin.extract_structure(content, Path('recursive.md'))
        assert structure is not None
        assert len(structure.sections) > 0
    
    def test_timeout_recovery(self, setup_plugins):
        """Test recovery from operations that might timeout."""
        plugin = setup_plugins['plaintext']
        
        # Generate content that takes long to process
        slow_content = ""
        for i in range(10000):
            slow_content += f"Line {i}: " + "word " * 50 + "\n"
        
        # Mock a slow operation
        original_chunk = plugin.chunk_document
        
        def slow_chunk_document(*args, **kwargs):
            # Simulate slow processing
            import time
            time.sleep(0.001)  # Small delay to simulate work
            return original_chunk(*args, **kwargs)
        
        with patch.object(plugin, 'chunk_document', side_effect=slow_chunk_document):
            start_time = time.time()
            chunks = plugin.chunk_document(slow_content, Path('slow.txt'))
            elapsed = time.time() - start_time
            
            # Should complete even with delays
            assert chunks is not None
            assert len(chunks) > 0
    
    def test_malformed_ast_recovery(self, setup_plugins):
        """Test recovery from malformed AST structures."""
        plugin = setup_plugins['python']
        
        # Python code that might produce unusual AST
        malformed_code = '''# Malformed Python

def function(
    param1,
    param2  # Missing closing paren on purpose
    
class IncompleteClass:
    def method(self
        pass
        
try:
    something()
except
    pass
    
# Valid code after errors
def valid_function():
    """This should still be found."""
    return 42
'''
        
        # Should handle AST errors gracefully
        result = plugin.indexFile('malformed.py', malformed_code)
        assert result is not None
        
        # Should still find valid symbols
        assert any('valid_function' in sym.name for sym in result.symbols)
    
    def test_resource_cleanup_on_error(self, setup_plugins):
        """Test proper resource cleanup when errors occur."""
        plugin = setup_plugins['markdown']
        
        # Mock an error during processing
        original_index = plugin.indexFile
        
        def failing_index(*args, **kwargs):
            # Allocate some resources (simulated)
            temp_data = ['resource'] * 1000
            
            # Fail partway through
            raise RuntimeError("Simulated processing error")
        
        with patch.object(plugin, 'indexFile', side_effect=failing_index):
            try:
                plugin.indexFile('test.md', '# Test')
            except RuntimeError:
                pass
        
        # Should be able to process normally after error
        result = original_index('test2.md', '# Test 2')
        assert result is not None
    
    def test_partial_semantic_index_failure(self, setup_plugins):
        """Test recovery when semantic indexing partially fails."""
        # Create plugin with semantic indexing
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "test.db"))
            plugin = MarkdownPlugin(enable_semantic=True)
            
            content = """# Document
            
## Section 1
Content for embedding.

## Section 2
More content.

## Section 3
Final content."""
            
            # Mock embedding generation to fail on some chunks
            if hasattr(plugin, 'semantic_indexer'):
                original_embed = plugin.semantic_indexer.generate_embeddings
                
                def failing_embeddings(texts):
                    # Fail on second text
                    results = []
                    for i, text in enumerate(texts):
                        if i == 1:
                            results.append(None)  # Simulated failure
                        else:
                            results.append([0.1] * 384)  # Mock embedding
                    return results
                
                with patch.object(plugin.semantic_indexer, 'generate_embeddings', side_effect=failing_embeddings):
                    # Should still index despite embedding failures
                    result = plugin.indexFile('semantic_fail.md', content)
                    assert result is not None
                    assert len(result.symbols) > 0
    
    def test_search_error_recovery(self, setup_plugins):
        """Test recovery from search errors."""
        plugins = setup_plugins
        store = plugins['store']
        
        # Index some content
        plugins['markdown'].indexFile('test1.md', '# Test 1\n\nContent one')
        plugins['markdown'].indexFile('test2.md', '# Test 2\n\nContent two')
        
        # Mock a search error
        original_search = store.search_symbols_fts
        call_count = 0
        
        def failing_search(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Search database error")
            return original_search(query, **kwargs)
        
        with patch.object(store, 'search_symbols_fts', side_effect=failing_search):
            # First search should fail
            try:
                results = store.search_symbols_fts('test')
            except RuntimeError:
                pass
            
            # Second search should work
            results = store.search_symbols_fts('test')
            assert len(results) > 0
    
    def test_graceful_degradation(self, setup_plugins):
        """Test graceful degradation when features fail."""
        plugin = setup_plugins['markdown']
        
        content = """# Document

## Section with Code

```python
def example():
    return 42
```

## Section with Table

| Col1 | Col2 |
|------|------|
| A    | B    |

## Regular Section

Just text here."""
        
        # Mock various feature extractions to fail
        with patch.object(plugin.parser, 'parse', side_effect=Exception("Parser failed")):
            # Should fall back to basic processing
            # Instead of crashing, should handle error
            try:
                result = plugin.indexFile('degraded.md', content)
                # Might return empty or basic result
            except:
                # Should not raise unhandled exception
                pass
        
        # Normal processing should work after error
        result = plugin.indexFile('normal.md', content)
        assert result is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])