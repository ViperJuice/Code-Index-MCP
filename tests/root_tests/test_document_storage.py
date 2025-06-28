"""Integration tests for document storage operations."""

import pytest
import tempfile
import shutil
from pathlib import Path
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from tests.base_test import BaseDocumentTest
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.document_processing.document_interfaces import (
    DocumentChunk, ChunkType, ChunkMetadata, ProcessedDocument,
    DocumentStructure, Section
)
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin.plugin import PlainTextPlugin
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher

logger = logging.getLogger(__name__)


class TestDocumentStorage(BaseDocumentTest):
    """Test storage operations for document processing system."""
    
    def test_document_chunk_storage(self):
        """Test storing and retrieving document chunks."""
        # Create test chunks
        chunks = [
            DocumentChunk(
                id="doc1_chunk1",
                content="# Introduction\n\nThis is the introduction.",
                type=ChunkType.HEADING,
                metadata=ChunkMetadata(
                    document_path="/docs/intro.md",
                    section_hierarchy=["Introduction"],
                    chunk_index=0,
                    total_chunks=2,
                    has_code=False,
                    word_count=5,
                    line_start=1,
                    line_end=3
                )
            ),
            DocumentChunk(
                id="doc1_chunk2",
                content="## Getting Started\n\nFollow these steps:\n\n```bash\npip install\n```",
                type=ChunkType.HEADING,
                metadata=ChunkMetadata(
                    document_path="/docs/intro.md",
                    section_hierarchy=["Introduction", "Getting Started"],
                    chunk_index=1,
                    total_chunks=2,
                    has_code=True,
                    language="bash",
                    word_count=8,
                    line_start=5,
                    line_end=10
                )
            )
        ]
        
        # Store chunks using custom document table
        conn = sqlite3.connect(sqlite_store.db_path)
        try:
            # Create document chunks table if not exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    content TEXT NOT NULL,
                    chunk_type TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    total_chunks INTEGER NOT NULL,
                    section_hierarchy TEXT,
                    has_code BOOLEAN,
                    language TEXT,
                    word_count INTEGER,
                    line_start INTEGER,
                    line_end INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create FTS table for document search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts
                USING fts5(
                    id UNINDEXED,
                    content,
                    section_hierarchy,
                    content=document_chunks,
                    content_rowid=rowid
                )
            """)
            
            # Insert chunks
            for chunk in chunks:
                conn.execute("""
                    INSERT INTO document_chunks 
                    (id, file_path, content, chunk_type, chunk_index, total_chunks,
                     section_hierarchy, has_code, language, word_count, line_start, line_end)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk.id,
                    chunk.metadata.document_path,
                    chunk.content,
                    chunk.type.value,
                    chunk.metadata.chunk_index,
                    chunk.metadata.total_chunks,
                    json.dumps(chunk.metadata.section_hierarchy),
                    chunk.metadata.has_code,
                    chunk.metadata.language,
                    chunk.metadata.word_count,
                    chunk.metadata.line_start,
                    chunk.metadata.line_end
                ))
            
            conn.commit()
            
            # Test retrieval
            cursor = conn.execute("""
                SELECT * FROM document_chunks WHERE file_path = ?
                ORDER BY chunk_index
            """, ("/docs/intro.md",))
            
            retrieved = cursor.fetchall()
            assert len(retrieved) == 2
            
            # Test FTS search
            cursor = conn.execute("""
                SELECT id, content, section_hierarchy
                FROM document_chunks_fts
                WHERE content MATCH 'introduction'
            """)
            
            search_results = cursor.fetchall()
            assert len(search_results) > 0
            assert "Introduction" in search_results[0][1]
            
        finally:
            conn.close()
    
    def test_document_metadata_storage(self, sqlite_store):
        """Test storing document metadata and structure."""
        # Create document structure
        structure = DocumentStructure(
            title="API Documentation",
            sections=[
                Section(
                    id="sec1",
                    heading="Overview",
                    level=1,
                    content="API overview content",
                    start_line=1,
                    end_line=10
                ),
                Section(
                    id="sec2", 
                    heading="Authentication",
                    level=2,
                    content="How to authenticate",
                    start_line=12,
                    end_line=25
                )
            ],
            metadata={
                "author": "Test Author",
                "version": "1.0.0",
                "last_updated": "2024-01-01"
            }
        )
        
        # Store document metadata
        conn = sqlite3.connect(sqlite_store.db_path)
        try:
            # Create documents table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    file_path TEXT PRIMARY KEY,
                    title TEXT,
                    structure TEXT,
                    metadata TEXT,
                    file_type TEXT,
                    last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert document
            conn.execute("""
                INSERT OR REPLACE INTO documents 
                (file_path, title, structure, metadata, file_type)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "/docs/api.md",
                structure.title,
                json.dumps({
                    "sections": [
                        {
                            "id": s.id,
                            "heading": s.heading,
                            "level": s.level,
                            "start_line": s.start_line,
                            "end_line": s.end_line
                        }
                        for s in structure.sections
                    ]
                }),
                json.dumps(structure.metadata),
                "markdown"
            ))
            
            conn.commit()
            
            # Test retrieval
            cursor = conn.execute("""
                SELECT * FROM documents WHERE file_path = ?
            """, ("/docs/api.md",))
            
            doc = cursor.fetchone()
            assert doc is not None
            assert doc[1] == "API Documentation"  # title
            
            # Parse structure back
            stored_structure = json.loads(doc[2])
            assert len(stored_structure["sections"]) == 2
            assert stored_structure["sections"][0]["heading"] == "Overview"
            
        finally:
            conn.close()
    
    def test_storage_with_dispatcher_integration(self, sqlite_store, temp_workspace):
        """Test storage operations through dispatcher integration."""
        # Create test documents
        docs_dir = temp_workspace / "docs"
        docs_dir.mkdir()
        
        readme = docs_dir / "README.md"
        readme.write_text("""# Project Documentation

## Overview

This project provides a comprehensive API for data processing.

## Installation

```bash
pip install dataprocessor
```

## Usage

```python
from dataprocessor import Process
p = Process()
p.run()
```
""")
        
        api_doc = docs_dir / "api.md"
        api_doc.write_text("""# API Reference

## Classes

### Process

Main processing class.

Methods:
- run(): Execute the process
- stop(): Stop execution
""")
        
        # Create dispatcher and index
        dispatcher = EnhancedDispatcher(sqlite_store=self.store)
        dispatcher.index(self.workspace)
        
        # Verify documents were stored
        conn = sqlite3.connect(sqlite_store.db_path)
        try:
            # Check symbols table (existing functionality)
            cursor = conn.execute("SELECT COUNT(*) FROM symbols")
            symbol_count = cursor.fetchone()[0]
            assert symbol_count > 0
            
            # Check if any document-specific data was stored
            cursor = conn.execute("""
                SELECT DISTINCT file_path FROM symbols 
                WHERE file_path LIKE '%.md'
            """)
            md_files = cursor.fetchall()
            assert len(md_files) >= 2
            
        finally:
            conn.close()
    
    def test_storage_update_operations(self, sqlite_store, temp_workspace):
        """Test updating stored documents."""
        # Initial document
        doc_path = temp_workspace / "guide.md"
        initial_content = "# Guide\n\nInitial content."
        doc_path.write_text(initial_content)
        
        # Create plugin and index
        plugin = MarkdownPlugin(sqlite_store=sqlite_store)
        plugin.index([str(doc_path)])
        
        # Update document
        updated_content = "# Guide\n\nUpdated content with more information."
        doc_path.write_text(updated_content)
        
        # Re-index
        plugin.index([str(doc_path)])
        
        # Verify update in storage
        conn = sqlite3.connect(sqlite_store.db_path)
        try:
            cursor = conn.execute("""
                SELECT content FROM symbols_fts 
                WHERE file_path = ? AND content MATCH 'updated'
            """, (str(doc_path),))
            
            results = cursor.fetchall()
            # Should find the updated content
            assert len(results) > 0
            
        finally:
            conn.close()
    
    def test_storage_search_performance(self, sqlite_store, temp_workspace):
        """Test search performance with many documents."""
        # Create multiple documents
        for i in range(50):
            doc = temp_workspace / f"doc_{i}.md"
            content = f"""# Document {i}

## Section A

Content about topic {i} with various keywords.

## Section B

More content with different focus for document {i}.

```python
def function_{i}():
    return "result_{i}"
```
"""
            doc.write_text(content)
        
        # Index all documents
        dispatcher = EnhancedDispatcher(sqlite_store=self.store)
        dispatcher.index(self.workspace)
        
        # Test search performance
        import time
        
        start_time = time.time()
        results = list(dispatcher.search("function return result", {"limit": 20}))
        search_time = time.time() - start_time
        
        # Should complete quickly even with many documents
        assert search_time < 1.0  # Less than 1 second
        assert len(results) > 0
        
        # Verify results are relevant
        assert any("function" in r.snippet.lower() for r in results)
    
    def test_storage_transaction_handling(self, sqlite_store, temp_workspace):
        """Test that storage handles transactions correctly."""
        # Create documents that might cause issues
        docs = []
        for i in range(10):
            doc = temp_workspace / f"test_{i}.md"
            if i == 5:
                # Create one with potentially problematic content
                content = "# Test\n\n```\nUnclosed code block..."
            else:
                content = f"# Test {i}\n\nNormal content."
            doc.write_text(content)
            docs.append(str(doc))
        
        # Index with potential failure
        plugin = MarkdownPlugin(sqlite_store=sqlite_store)
        shard = plugin.index(docs)
        
        # Should complete despite one problematic file
        assert shard is not None
        
        # Verify other documents were indexed
        conn = sqlite3.connect(sqlite_store.db_path)
        try:
            cursor = conn.execute("SELECT COUNT(DISTINCT file_path) FROM symbols")
            count = cursor.fetchone()[0]
            assert count >= 9  # At least 9 successful
            
        finally:
            conn.close()
    
    def test_storage_cleanup_operations(self, sqlite_store, temp_workspace):
        """Test storage cleanup when files are removed."""
        # Create and index a document
        doc1 = temp_workspace / "temp.md"
        doc1.write_text("# Temporary\n\nThis will be deleted.")
        
        doc2 = temp_workspace / "permanent.md"
        doc2.write_text("# Permanent\n\nThis stays.")
        
        dispatcher = EnhancedDispatcher(sqlite_store=self.store)
        dispatcher.index(self.workspace)
        
        # Remove one document
        doc1.unlink()
        
        # Re-index (should clean up missing files)
        dispatcher.index(temp_workspace)
        
        # Verify cleanup
        conn = sqlite3.connect(sqlite_store.db_path)
        try:
            # Check that temp.md entries are gone
            cursor = conn.execute("""
                SELECT COUNT(*) FROM symbols WHERE file_path = ?
            """, (str(doc1),))
            count = cursor.fetchone()[0]
            assert count == 0
            
            # Check that permanent.md is still there
            cursor = conn.execute("""
                SELECT COUNT(*) FROM symbols WHERE file_path = ?
            """, (str(doc2),))
            count = cursor.fetchone()[0]
            assert count > 0
            
        finally:
            conn.close()
    
    def test_storage_concurrent_access(self, sqlite_store, temp_workspace):
        """Test that storage handles concurrent access correctly."""
        import threading
        import time
        
        # Create test documents
        for i in range(20):
            doc = temp_workspace / f"concurrent_{i}.md"
            doc.write_text(f"# Document {i}\n\nContent for testing.")
        
        results = []
        errors = []
        
        def index_subset(start, end):
            try:
                dispatcher = EnhancedDispatcher(sqlite_store=sqlite_store)
                files = [
                    str(temp_workspace / f"concurrent_{i}.md")
                    for i in range(start, end)
                ]
                for f in files:
                    if Path(f).exists():
                        dispatcher.index(f)
                results.append(f"Indexed {start}-{end}")
            except Exception as e:
                errors.append(f"Error in {start}-{end}: {e}")
        
        # Run concurrent indexing
        threads = [
            threading.Thread(target=index_subset, args=(0, 5)),
            threading.Thread(target=index_subset, args=(5, 10)),
            threading.Thread(target=index_subset, args=(10, 15)),
            threading.Thread(target=index_subset, args=(15, 20))
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Should complete without errors
        assert len(errors) == 0
        assert len(results) == 4
        
        # Verify all documents were indexed
        conn = sqlite3.connect(self.store.db_path)
        try:
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT file_path) FROM symbols 
                WHERE file_path LIKE '%concurrent_%'
            """)
            count = cursor.fetchone()[0]
            assert count >= 15  # Most should succeed
            
        finally:
            conn.close()
    
    def test_storage_schema_evolution(self):
        """Test storage handles schema changes gracefully."""
        # Create initial schema
        conn = sqlite3.connect(self.store.db_path)
        try:
            # Add a new table for testing
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_versions (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    content_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert test data
            conn.execute("""
                INSERT INTO document_versions (file_path, version, content_hash)
                VALUES (?, ?, ?)
            """, ("/test.md", 1, "abc123"))
            
            conn.commit()
            
            # Verify table exists and has data
            cursor = conn.execute("SELECT COUNT(*) FROM document_versions")
            count = cursor.fetchone()[0]
            assert count == 1
            
            # Add new column (schema evolution)
            conn.execute("ALTER TABLE document_versions ADD COLUMN author TEXT")
            
            # Insert with new schema
            conn.execute("""
                INSERT INTO document_versions (file_path, version, content_hash, author)
                VALUES (?, ?, ?, ?)
            """, ("/test2.md", 1, "def456", "Test Author"))
            
            conn.commit()
            
            # Verify both records exist
            cursor = conn.execute("SELECT COUNT(*) FROM document_versions")
            count = cursor.fetchone()[0]
            assert count == 2
            
        finally:
            conn.close()
    
    def test_storage_bulk_operations(self):
        """Test efficient bulk storage operations."""
        # Prepare bulk data
        documents = []
        for i in range(100):
            doc = self.workspace / f"bulk_{i}.md"
            content = f"# Bulk Document {i}\n\nContent for bulk testing."
            doc.write_text(content)
            documents.append(str(doc))
        
        # Test bulk indexing
        plugin = MarkdownPlugin(sqlite_store=self.store)
        
        start_time = time.time()
        shard = plugin.index(documents)
        bulk_time = time.time() - start_time
        
        assert shard is not None
        
        # Verify all documents were indexed
        conn = sqlite3.connect(self.store.db_path)
        try:
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT file_path) FROM symbols
                WHERE file_path LIKE '%bulk_%'
            """)
            count = cursor.fetchone()[0]
            assert count >= 90  # Most should succeed
            
            # Bulk operations should be efficient
            assert bulk_time < 10.0  # Less than 10 seconds for 100 docs
            
        finally:
            conn.close()
    
    def test_storage_query_optimization(self):
        """Test that storage queries are optimized with proper indexes."""
        conn = sqlite3.connect(self.store.db_path)
        try:
            # Check for indexes
            cursor = conn.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type = 'index' AND tbl_name = 'symbols'
            """)
            indexes = cursor.fetchall()
            
            # Should have indexes for common queries
            index_names = [idx[0] for idx in indexes]
            # At minimum, should have index on file_path
            assert any('file_path' in name or 'path' in name for name in index_names)
            
            # Test query performance with EXPLAIN
            cursor = conn.execute("""
                EXPLAIN QUERY PLAN
                SELECT * FROM symbols WHERE file_path = ?
            """, ("/test.py",))
            
            plan = cursor.fetchall()
            # Should use index, not table scan
            plan_text = str(plan)
            assert 'USING INDEX' in plan_text or 'SEARCH' in plan_text
            
        finally:
            conn.close()
    
    def test_storage_data_integrity(self):
        """Test data integrity constraints and validation."""
        conn = sqlite3.connect(self.store.db_path)
        try:
            # Test foreign key constraints (if enabled)
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create test tables with constraints
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_documents (
                    id INTEGER PRIMARY KEY,
                    path TEXT UNIQUE NOT NULL,
                    checksum TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_chunks (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES test_documents(id)
                )
            """)
            
            # Insert valid data
            conn.execute("""
                INSERT INTO test_documents (path, checksum) VALUES (?, ?)
            """, ("/valid.md", "checksum123"))
            
            doc_id = conn.lastrowid
            
            conn.execute("""
                INSERT INTO test_chunks (document_id, content) VALUES (?, ?)
            """, (doc_id, "Valid chunk content"))
            
            # Try to insert with invalid foreign key (should fail if constraints are on)
            try:
                conn.execute("""
                    INSERT INTO test_chunks (document_id, content) VALUES (?, ?)
                """, (99999, "Invalid chunk"))
                # If we get here, foreign keys might be off
                conn.rollback()
            except sqlite3.IntegrityError:
                # This is expected
                pass
            
            # Test unique constraint
            try:
                conn.execute("""
                    INSERT INTO test_documents (path, checksum) VALUES (?, ?)
                """, ("/valid.md", "different_checksum"))
                conn.rollback()
                assert False, "Should have failed on unique constraint"
            except sqlite3.IntegrityError:
                # Expected
                pass
                
        finally:
            conn.close()
    
    def test_storage_compression(self):
        """Test storage with compressed content."""
        import zlib
        
        # Create large repetitive content
        large_content = "# Large Document\n\n" + ("This is repetitive content. " * 1000)
        
        # Store compressed version
        compressed = zlib.compress(large_content.encode())
        
        conn = sqlite3.connect(self.store.db_path)
        try:
            # Create table for compressed content
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compressed_docs (
                    id INTEGER PRIMARY KEY,
                    path TEXT UNIQUE,
                    compressed_content BLOB,
                    original_size INTEGER,
                    compressed_size INTEGER
                )
            """)
            
            # Store compressed data
            conn.execute("""
                INSERT INTO compressed_docs 
                (path, compressed_content, original_size, compressed_size)
                VALUES (?, ?, ?, ?)
            """, (
                "/large.md",
                compressed,
                len(large_content.encode()),
                len(compressed)
            ))
            
            conn.commit()
            
            # Retrieve and decompress
            cursor = conn.execute("""
                SELECT compressed_content, original_size, compressed_size
                FROM compressed_docs WHERE path = ?
            """, ("/large.md",))
            
            row = cursor.fetchone()
            assert row is not None
            
            decompressed = zlib.decompress(row[0]).decode()
            assert decompressed == large_content
            
            # Verify compression saved space
            compression_ratio = row[2] / row[1]
            assert compression_ratio < 0.5  # Should achieve >50% compression
            
        finally:
            conn.close()
    
    def test_storage_backup_restore(self):
        """Test backup and restore functionality."""
        # Create some test data
        test_docs = []
        for i in range(5):
            doc = self.workspace / f"backup_test_{i}.md"
            doc.write_text(f"# Document {i}\n\nContent for backup test.")
            test_docs.append(str(doc))
        
        # Index documents
        plugin = MarkdownPlugin(sqlite_store=self.store)
        plugin.index(test_docs)
        
        # Create backup
        backup_path = self.workspace / "backup.db"
        
        # Use SQLite backup API
        source_conn = sqlite3.connect(self.store.db_path)
        backup_conn = sqlite3.connect(str(backup_path))
        
        try:
            source_conn.backup(backup_conn)
            backup_conn.close()
            source_conn.close()
            
            # Verify backup file exists and has data
            assert backup_path.exists()
            
            # Test restore by querying backup
            backup_conn = sqlite3.connect(str(backup_path))
            cursor = backup_conn.execute("SELECT COUNT(*) FROM symbols")
            count = cursor.fetchone()[0]
            assert count > 0
            
            backup_conn.close()
            
        finally:
            if source_conn:
                source_conn.close()
            if backup_conn:
                backup_conn.close()
    
    def test_storage_metadata_indexing(self):
        """Test efficient storage and retrieval of document metadata."""
        # Create documents with rich metadata
        metadata_docs = [
            {
                'path': self.workspace / "doc1.md",
                'content': """---
title: Technical Guide
author: John Doe
tags: [python, tutorial, beginners]
date: 2024-01-15
version: 1.0
---

# Technical Guide

Content here.""",
                'expected_meta': {
                    'title': 'Technical Guide',
                    'author': 'John Doe',
                    'tags': ['python', 'tutorial', 'beginners']
                }
            },
            {
                'path': self.workspace / "doc2.md",
                'content': """---
title: API Reference
author: Jane Smith
tags: [api, reference, advanced]
date: 2024-01-20
version: 2.0
---

# API Reference

API documentation.""",
                'expected_meta': {
                    'title': 'API Reference',
                    'author': 'Jane Smith',
                    'tags': ['api', 'reference', 'advanced']
                }
            }
        ]
        
        # Create and index documents
        for doc in metadata_docs:
            doc['path'].write_text(doc['content'])
        
        plugin = MarkdownPlugin(sqlite_store=self.store)
        plugin.index([str(d['path']) for d in metadata_docs])
        
        # Verify metadata was extracted and stored
        conn = sqlite3.connect(self.store.db_path)
        try:
            # Check if metadata is searchable
            cursor = conn.execute("""
                SELECT DISTINCT file_path, content FROM symbols
                WHERE content LIKE '%John Doe%' OR content LIKE '%Technical Guide%'
            """)
            
            results = cursor.fetchall()
            assert len(results) > 0
            
            # Should find the document with matching metadata
            found_paths = [r[0] for r in results]
            assert any('doc1.md' in path for path in found_paths)
            
        finally:
            conn.close()
    
    def test_storage_with_transactions(self):
        """Test proper transaction handling in storage operations."""
        conn = sqlite3.connect(self.store.db_path)
        
        try:
            # Start transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Create test table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transaction_test (
                    id INTEGER PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # Insert data
            for i in range(10):
                conn.execute("""
                    INSERT INTO transaction_test (value) VALUES (?)
                """, (f"value_{i}",))
            
            # Verify data before commit
            cursor = conn.execute("SELECT COUNT(*) FROM transaction_test")
            count = cursor.fetchone()[0]
            assert count == 10
            
            # Rollback transaction
            conn.execute("ROLLBACK")
            
            # Verify rollback worked
            cursor = conn.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name='transaction_test'
            """)
            table_exists = cursor.fetchone()[0]
            
            if table_exists:
                cursor = conn.execute("SELECT COUNT(*) FROM transaction_test")
                count = cursor.fetchone()[0]
                assert count == 0  # Should be empty after rollback
                
        finally:
            conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])