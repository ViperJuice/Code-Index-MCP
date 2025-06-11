# BM25 Index Population Script

## Overview

The `populate_bm25_index.py` script efficiently indexes all files from the SQLite database into BM25 full-text search tables using parallel processing. This enables fast keyword-based searching with BM25 ranking.

## Features

- **Parallel Processing**: Uses multiple workers to index files concurrently
- **Progress Tracking**: Real-time progress updates with ETA
- **Error Handling**: Graceful handling of file read errors and encoding issues
- **Metadata Preservation**: Maintains all original file metadata from the database
- **Language-Aware**: Extracts language-specific symbols, imports, and comments
- **Incremental Updates**: Skips files with unchanged content (unless forced)
- **Memory Efficient**: Processes files in batches to handle large codebases

## Usage

### Basic Usage

```bash
# Index all files in the database
python scripts/populate_bm25_index.py

# With verbose output
python scripts/populate_bm25_index.py --verbose
```

### Advanced Options

```bash
# Index only Python files
python scripts/populate_bm25_index.py --language python

# Index files from a specific repository
python scripts/populate_bm25_index.py --repository /path/to/repo

# Force reindex all files
python scripts/populate_bm25_index.py --force

# Custom batch size and worker count
python scripts/populate_bm25_index.py --batch-size 200 --workers 8

# Use a different database
python scripts/populate_bm25_index.py --db-path /path/to/database.db
```

## Command Line Options

- `--db-path PATH`: Path to SQLite database (default: code_index.db)
- `--batch-size SIZE`: Number of files to process per batch (default: 100)
- `--workers NUM`: Number of parallel workers (default: CPU count)
- `--language LANG`: Only index files of specific language
- `--repository REPO`: Only index files from specific repository path
- `--force`: Force reindex even if content hasn't changed
- `--verbose`: Enable verbose logging

## How It Works

1. **File Discovery**: Queries the SQLite database for all files matching the filters
2. **Batch Processing**: Divides files into batches for parallel processing
3. **Content Reading**: Reads file content from disk with encoding detection
4. **Metadata Extraction**: Uses language-specific plugins to extract:
   - Symbol definitions (classes, functions, methods)
   - Import statements
   - Comments and documentation
5. **BM25 Indexing**: Indexes content into FTS5 tables with:
   - Full file content
   - Extracted symbols
   - File metadata
6. **Progress Tracking**: Reports progress with statistics:
   - Files processed
   - Success/failure counts
   - Processing rate
   - Estimated time remaining
7. **Index Optimization**: Optimizes FTS5 tables after bulk loading

## Performance

The script is optimized for large codebases:

- **Parallel Processing**: Utilizes all CPU cores by default
- **Batch Operations**: Reduces database transaction overhead
- **Memory Efficiency**: Processes files in streams, not loading entire codebase
- **Skip Large Files**: Automatically skips files over 10MB
- **Encoding Detection**: Tries multiple encodings to maximize readable files

### Expected Performance

- Small projects (<1000 files): 1-5 seconds
- Medium projects (1000-10000 files): 10-60 seconds  
- Large projects (10000-100000 files): 1-10 minutes
- Very large monorepos (>100000 files): 10-30 minutes

## Error Handling

The script handles various error conditions:

- **Missing Files**: Logs warning and continues
- **Encoding Errors**: Tries multiple encodings, skips if all fail
- **Large Files**: Skips files over 10MB with warning
- **Plugin Errors**: Logs warning but still indexes file content
- **Database Errors**: Rolls back transaction and logs error

## Integration

After indexing, you can search using:

```python
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer

storage = SQLiteStore("code_index.db")
indexer = BM25Indexer(storage)

# Search for content
results = indexer.search("TODO", limit=10)

# Search for symbols
symbol_results = indexer.search("MyClass", search_type="symbols")

# Phrase search
phrase_results = indexer.search_phrase("import sqlite3")
```

## Monitoring

The script provides detailed progress information:

```
2024-01-10 10:30:00 - Starting BM25 indexing with 8 workers
2024-01-10 10:30:00 - Found 5432 files to index
2024-01-10 10:30:05 - Progress: 500/5432 files (9.2%) - Rate: 100.0 files/sec - ETA: 49s
2024-01-10 10:30:10 - Progress: 1000/5432 files (18.4%) - Rate: 102.3 files/sec - ETA: 43s
...
2024-01-10 10:30:54 - Indexing completed in 54.2 seconds
2024-01-10 10:30:54 - Total files: 5432
2024-01-10 10:30:54 - Successfully indexed: 5420
2024-01-10 10:30:54 - Failed: 12
2024-01-10 10:30:54 - Average rate: 100.2 files/second
```

## Troubleshooting

### Common Issues

1. **"File not found" errors**
   - Files may have been moved/deleted since database was populated
   - Re-run main indexing to update file paths

2. **Encoding errors**
   - Some files may use uncommon encodings
   - Script tries UTF-8, UTF-8-BOM, Latin-1, and CP1252

3. **Memory usage**
   - Reduce batch size: `--batch-size 50`
   - Reduce workers: `--workers 2`

4. **Slow performance**
   - Check disk I/O performance
   - Ensure database is on fast storage (SSD)
   - Run with `--verbose` to identify bottlenecks

## Related Tools

- `mcp_server_cli.py index`: Initial file discovery and indexing
- `demo_populate_bm25.py`: Demo script showing BM25 usage
- `test_bm25_hybrid_search.py`: Test hybrid search capabilities